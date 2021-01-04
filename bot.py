#!/usr/bin/env python

import discord
import yaml
import os
import numpy
import imageio
import requests
from io import StringIO, BytesIO
from mtg_pack_generator.mtg_pack_generator import MtgPackGenerator

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

client = discord.Client()
generator = MtgPackGenerator(config["mtgjson_path"])
historic_sets = ["klr", "akr", "xln", "rix", "dom", "m19", "grn", "rna",
                 "war", "m20", "eld", "thb", "iko", "m21", "znr"]
standard_sets = ["eld", "thb", "iko", "m21", "znr"]


def upload_img(file):
    '''Upload an image file to imgur.com and returns the link'''
    url = "https://api.imgur.com/3/image"

    headers = {"Authorization": f"Client-ID {config['imgur_client_id']}"}
    payload = {'image': file.getvalue()}

    response = requests.request("POST", url, headers=headers, data=payload)
    assert(response.status_code == requests.codes.ok)

    return response.json()["data"]["link"]


def pack_img(im_list):
    '''Generate an image of the cards in a pack over two rows'''
    assert(len(im_list))
    cards_per_row = int(numpy.ceil(len(im_list) / 2))
    row1 = im_list[0]
    row2 = im_list[cards_per_row]
    for i in range(1, len(im_list)):
        if i < cards_per_row:
            row1 = numpy.hstack((row1, im_list[i]))
        if i > cards_per_row:
            row2 = numpy.hstack((row2, im_list[i]))
    pad_amount = row1.shape[1]-row2.shape[1]
    row2 = numpy.pad(row2, [[0, 0], [0, pad_amount], [
                     0, 0]], 'constant', constant_values=255)
    return numpy.vstack((row1, row2))


@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    command = message.content.lower()
    p = p_list = None
    if command == "!random":
        p = generator.get_random_pack()
    elif command == "!historic":
        p = generator.get_random_pack(historic_sets)
    elif command == "!standard":
        p = generator.get_random_pack(standard_sets)
    elif command in [f"!{set}" for set in historic_sets]:
        p = generator.get_pack(command.lstrip("!"))
    elif command == "!chaossealed":
        p_list = generator.get_random_pack(historic_sets, n=6)
    elif command in [f"!{set}sealed" for set in historic_sets]:
        p_list = generator.get_pack(command.lstrip("!").rstrip("sealed"), n=6)
    elif command == "!help":
        await message.channel.send(
            "you can give it one of the following commands atm:\n"
            "`!random`: generates a random pack from the whole history "
            "of Magic\n"
            "`!historic`: generates a random historic pack\n"
            "`!standard`: generates a random standard pack\n"
            "`!{setcode}`: generates a pack from the indicated set, available "
            "on Arena (e.g., `!znr` generates a *Zendikar Rising* pack)\n"
            "`!{setcode}sealed`: generates 6 packs from the indicated set, "
            "available on Arena (e.g., `!znrsealed` generates 6 *Zendikar "
            "Rising* packs)\n"
            "`!chaossealed`: generates 6 random historic packs\n"
            "`!help`: shows this message"
        )

    if p:
        # First send the booster text with a loading message for the image
        embed = discord.Embed(
            description=u"Creating booster image... :hourglass:",
            color=discord.Color.orange()
        )
        m = await message.channel.send(f"**{p.name}** (generated by "
                                       f"{message.author.mention})\n"
                                       f"```\n{p.get_arena_format()}\n```",
                                       embed=embed)

        # Then generate the image of the booster content (takes a while)
        p_img = pack_img(p.get_images(size="normal"))
        file = BytesIO()
        imageio.imwrite(file, p_img, format="jpeg")

        # Upload it to imgur.com
        link = upload_img(file)

        # Then edit the message by embedding the link
        embed = discord.Embed(color=discord.Color.dark_green())
        embed.set_image(url=link)
        await m.edit(embed=embed)
    elif p_list:
        pool = ""
        sets = ""
        for p in p_list:
            sets = sets + f"{p.set.code}, "
            pool = pool + f"{p.get_arena_format()}\n"
        sets = sets + ""
        file = StringIO(pool)
        await message.channel.send(f"**Sealed starting pool** "
                                   f"(generated by {message.author.mention})\n"
                                   f"Content: [{sets.rstrip(', ')}]",
                                   file=discord.File(
                                       file,
                                       filename=f"{message.author}_pool.txt"))

client.run(config["discord_token"])
