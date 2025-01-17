import re
from io import BytesIO

import imageio
import numpy as np
import pytest
from aioresponses import aioresponses
from boostertutor.models.mtg_card import MtgCard
from boostertutor.models.mtg_pack import MtgPack


def test_duplicates(unbalanced_pack: MtgPack):
    assert not unbalanced_pack.has_duplicates()
    card = unbalanced_pack.content["nonlandCommon"]["cards"][0]
    unbalanced_pack.content["nonlandCommon"]["cards"].append(card)
    assert unbalanced_pack.has_duplicates()


def test_duplicates_in_foil(unbalanced_pack: MtgPack):
    card = unbalanced_pack.content["nonlandCommon"]["cards"][0]
    card.foil = True
    unbalanced_pack.content["foil"] = {"cards": [card], "balance": False}
    assert not unbalanced_pack.has_duplicates()


@pytest.mark.parametrize("count_hybrids", [True, False])
def test_count_card_colors(cards: dict[str, MtgCard], count_hybrids: bool):
    card_list = list(cards.values())
    pack = MtgPack({"slot": {"cards": card_list}})
    colors, counts = pack.count_cards_colors(
        card_list, count_hybrids=count_hybrids
    )
    assert counts == {
        "W": 2 if count_hybrids else 1,
        "U": 1,
        "B": 1,
        "R": 1,
        "G": 2 if count_hybrids else 1,
        "C": 2,
    }


def test_arena(cards: dict[str, MtgCard]):
    card_list = [cards["Electrolyze"], cards["Mysterious Egg"]]
    pack = MtgPack({"slot": {"cards": card_list}})
    assert (
        pack.arena_format()
        == "1 Mysterious Egg (IKO) 3\n1 Electrolyze (STA) 123"
    )


def test_json(cards: dict[str, MtgCard]):
    card_list = [cards["Electrolyze"], cards["Mysterious Egg"]]
    pack = MtgPack({"slot": {"cards": card_list}})
    assert pack.json() == [
        {"name": "Mysterious Egg", "count": 1},
        {"name": "Electrolyze", "count": 1},
    ]


def test_balancing(unbalanced_pack: MtgPack):
    assert not unbalanced_pack.is_balanced()
    unbalanced_pack.is_balanced(rebalance=True)
    assert unbalanced_pack.is_balanced()

    cards = [c.card.name for c in unbalanced_pack.cards]
    assert "Griffin Protector" not in cards
    assert "Fortress Crab" in cards


async def test_image(unbalanced_pack: MtgPack):
    pattern = re.compile(r"^https://api\.scryfall\.com/cards.*$")
    expected_img = np.zeros((10, 10, 3))
    mock_img_file = BytesIO()
    imageio.imwrite(mock_img_file, expected_img, format="jpeg")
    with aioresponses() as mocked:
        mocked.get(
            url=pattern, status=200, body=mock_img_file.getvalue(), repeat=True
        )
        img_list = await unbalanced_pack.get_images()

        assert len(img_list) == len(unbalanced_pack.cards)
        assert all([i.shape == (10, 10, 3) for i in img_list])
