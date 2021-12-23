import os
from io import BytesIO, StringIO
from typing import Optional, Any

import aiohttp
import discord
import imageio
import yaml

import boostertutor.utils.utils as utils
from boostertutor.generator import MtgPackGenerator


class Bot:
    def __init__(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "..", "config.yaml")) as file:
            self.config: dict[str, Any] = yaml.load(
                file, Loader=yaml.FullLoader
            )

        self.pack_log: bool = self.config.get("pack_logging", True)
        self.generator = MtgPackGenerator(
            path_to_mtgjson=self.config["mtgjson_path"],
            path_to_jmp=self.config.get("jmp_decklists_path", None),
            jmp_arena=True,
        )
        self.standard_sets = ["znr", "khm", "stx", "afr", "mid", "vow"]
        self.historic_sets = [
            "klr",
            "akr",
            "xln",
            "rix",
            "dom",
            "m19",
            "grn",
            "rna",
            "war",
            "m20",
            "eld",
            "thb",
            "iko",
            "m21",
            "znr",
            "khm",
            "stx",
            "afr",
            "mid",
            "vow",
        ]
        self.all_sets: list[str] = [
            s.lower() for s in self.generator.sets_with_boosters
        ]


class DiscordBot(Bot, discord.Client):
    def __init__(self) -> None:
        Bot.__init__(self)
        discord.Client.__init__(self)
        self.prefix: str = self.config["command_prefix"]

    def emoji(self, name: str, guild: Optional[discord.Guild] = None) -> str:
        """Return an emoji if it exists on the server or empty otherwise"""
        for e in guild.emojis if guild else self.emojis:
            if e.name == name:
                return str(e)
        return ""

    async def on_ready(self) -> None:
        print(f"{self.user} has connected to Discord!")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if not message.content.startswith(self.prefix):
            return

        argv = message.content.removeprefix(self.prefix).split()
        assert len(argv)
        command = argv[0].lower()
        if len(message.mentions):
            member = message.mentions[0]
        else:
            member = message.author

        p = p_list = None
        em = ""
        if command == "random":
            p = self.generator.get_random_packs(log=self.pack_log)[0]
        elif command == "historic":
            p = self.generator.get_random_packs(
                self.historic_sets, log=self.pack_log
            )[0]
        elif command == "standard":
            p = self.generator.get_random_packs(
                self.standard_sets, log=self.pack_log
            )[0]
        elif command == "jmp":
            if self.jmp is not None:
                p = self.generator.get_random_jmp_decks(log=self.pack_log)[0]
        elif command in self.all_sets:
            p = self.generator.get_pack(command, log=self.pack_log)
        elif command == "chaossealed":
            em = self.emoji("CHAOS", message.guild)
            p_list = self.generator.get_random_packs(
                self.historic_sets, n=6, log=self.pack_log
            )
        elif command.removesuffix("sealed") in self.all_sets:
            em = self.emoji(
                command.removesuffix("sealed").upper(), message.guild
            )
            p_list = self.generator.get_packs(
                command.removesuffix("sealed"), n=6, log=self.pack_log
            )
        elif command == "jmpsealed":
            if self.jmp is not None:
                em = self.emoji("JMP", message.guild)
                p_list = self.generator.get_random_jmp_decks(
                    n=3, log=self.pack_log
                )
        elif command == "help":
            await message.channel.send(
                f"You can give me one of the following commands:\n"
                f"> `{self.prefix}random`: generates a random pack from the "
                f"whole history of Magic\n"
                f"> `{self.prefix}historic`: generates a random historic "
                f"pack\n"
                f"> `{self.prefix}standard`: generates a random standard "
                f"pack\n"
                f"> `{self.prefix}{{setcode}}`: generates a pack from the "
                f"indicated set (e.g., `{self.prefix}znr` generates a "
                f"*Zendikar Rising* pack)\n"
                f"> `{self.prefix}{{setcode}}sealed`: generates 6 packs from "
                f"the indicated set (e.g., `{self.prefix}znrsealed` generates "
                f"6 *Zendikar Rising* packs)\n"
                f"> `{self.prefix}chaossealed`: generates 6 random historic "
                f"packs\n"
                f"> `{self.prefix}addpack xyz123`: if issued replying to a "
                f"pack I have generated, adds that pack to the previously "
                f"generated sealeddeck.tech pool with ID `xyz123`\n"
                f"> `{self.prefix}help`: shows this message\n"
                f"While replying to any command, I will mention the user who "
                f"issued it, unless the command is followed by a mention, in "
                f"which case I will mention that user instead. For example, "
                f"`{self.prefix}znr @user` has me mention *user* (instead of "
                f"you) in my reply."
            )
        elif command == "addpack":
            if len(argv) != 2 or not message.reference:
                await message.channel.send(
                    f"{message.author.mention}\n"
                    "To add a pack to the sealeddeck.tech pool `xyz123`, reply"
                    " to my message with the pack content with the command "
                    f"`{self.prefix}addpack xyz123`"
                )
            else:
                ref = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if (
                    ref.author != self.user
                    or len(ref.content.split("```")) < 2
                ):
                    await message.channel.send(
                        f"{message.author.mention}\n"
                        "The message you are replying to does not contain a "
                        "pack I have generated"
                    )
                else:
                    ref_pack = ref.content.split("```")[1].strip()

                    sealeddeck_id = argv[1].strip()

                    pack_json = utils.arena_to_json(ref_pack)
                    m = await message.channel.send(
                        f"{message.author.mention}\n"
                        f":hourglass: Adding pack to pool..."
                    )
                    try:
                        new_id = await utils.pool_to_sealeddeck(
                            pack_json, sealeddeck_id
                        )
                    except aiohttp.ClientResponseError as e:
                        print(f"Sealeddeck error: {e}")
                        content = (
                            f"{message.author.mention}\n"
                            f"The pack could not be added to sealeddeck.tech "
                            f"pool with ID `{sealeddeck_id}`. Please, verify "
                            f"the ID.\n"
                            f"If the ID is correct, sealeddeck.tech might be "
                            f"having some issues right now, try again later."
                        )

                    else:
                        content = (
                            f"{message.author.mention}\n"
                            f"The pack has been added to the pool.\n\n"
                            f"**Updated sealeddeck.tech pool**\n"
                            f"link: https://sealeddeck.tech/{new_id}\n"
                            f"ID: `{new_id}`"
                        )
                    await m.edit(content=content)

        if p:
            # First send the booster text with a loading message for the image
            embed = discord.Embed(
                description=":hourglass: Summoning a vision of your booster "
                "from the aether...",
                color=discord.Color.orange(),
            )
            em = self.emoji(p.set.code.upper(), message.guild)

            m = await message.channel.send(
                f"**{em}{(' ' if len(em) else '')}{p.name}**\n"
                f"{member.mention}\n"
                f"```\n{p.arena_format()}\n```",
                embed=embed,
            )

            try:
                # Then generate the image of booster content (takes a while)
                img_list = await p.get_images(size="normal")
                p_img = utils.pack_img(img_list)
                img_file = BytesIO()
                imageio.imwrite(img_file, p_img, format="jpeg")

                # Upload it to imgur.com
                link = await utils.upload_img(
                    img_file, self.config["imgur_client_id"]
                )
            except aiohttp.ClientResponseError:
                # Send an error message if the upload failed...
                embed = discord.Embed(
                    description=":x: Sorry, it seems your booster is lost in "
                    "the Blind Eternities...",
                    color=discord.Color.red(),
                )
            else:
                # ...or edit the message by embedding the link
                embed = discord.Embed(
                    color=discord.Color.dark_green(), description=link
                )
                embed.set_image(url=link)

            await m.edit(embed=embed)
        elif p_list:
            pool_file = StringIO(
                "\r\n".join([p.arena_format() for p in p_list])
            )
            sets = ", ".join([p.set.code for p in p_list])
            json_pool = [card_json for p in p_list for card_json in p.json()]

            # First send the pool content with a loading message for the image
            embed = discord.Embed(
                description=":hourglass: Summoning a vision of your rares "
                "from the aether...",
                color=discord.Color.orange(),
            )
            m = await message.channel.send(
                f"**{em}{(' ' if len(em) else '')}Sealed pool**\n"
                f"{member.mention}\n"
                f"Content: [{sets}]",
                embed=embed,
                file=discord.File(
                    pool_file, filename=f"{member.nick}_pool.txt"
                ),
            )

            content = m.content
            try:
                sealeddeck_id = await utils.pool_to_sealeddeck(json_pool)
            except aiohttp.ClientResponseError as e:
                print(f"Sealeddeck error: {e}")
                content += "\n\n**Sealeddeck.tech:** Error\n"
            else:
                content += (
                    f"\n\n**Sealeddeck.tech link:** "
                    f"https://sealeddeck.tech/{sealeddeck_id}"
                    f"\n**Sealeddeck.tech ID:** "
                    f"`{sealeddeck_id}`"
                )

            await m.edit(content=content)

            try:
                # Then generate the image of rares in pool (takes a while)
                img_list = [
                    await c.get_image(size="normal")
                    for p in p_list
                    for c in p.cards
                    if c.card.rarity in ["rare", "mythic"]
                ]
                r_img = utils.rares_img(img_list)
                r_file = BytesIO()
                imageio.imwrite(r_file, r_img, format="jpeg")

                # Upload it to imgur.com
                link = await utils.upload_img(
                    r_file, self.config["imgur_client_id"]
                )
            except aiohttp.ClientResponseError:
                # Send an error message if the upload failed...
                embed = discord.Embed(
                    description=":x: Sorry, it seems your rares are lost in "
                    "the Blind Eternities...",
                    color=discord.Color.red(),
                )
            else:
                # ...or edit the message by embedding the link
                embed = discord.Embed(
                    color=discord.Color.dark_green(), description=link
                )
                embed.set_image(url=link)

            await m.edit(embed=embed)
