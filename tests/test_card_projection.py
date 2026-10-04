import copy

import pytest

from compositor.card_projection import card_to_source, project_card
from compositor.package import CompositionError
from test_scene_contribution import lab


def test_surface_and_audience_selection_with_readback(tmp_path):
    _, context, contribution = lab(tmp_path)
    gm = project_card(contribution, context, audience="GM", active_surface="Planning")
    assert gm["lenses"]["do_now"][0]["id"] == "offer"
    assert gm["choices"][0]["mode"] == "optional"
    assert card_to_source(gm, "offer", context)[0]["quote"] == "The keeper offers a safe crossing."
    player = project_card(contribution, context, audience="PLAYER", active_surface="Playing")
    assert all(not entries for entries in player["lenses"].values())
    assert player["choices"] == []
    altered = copy.deepcopy(gm)
    altered["source"]["package_revision"] = "b" * 64
    with pytest.raises(CompositionError, match="revision"):
        card_to_source(altered, "offer", context)


def test_read_aloud_requires_explicit_review(tmp_path):
    _, context, contribution = lab(tmp_path)
    claim = contribution["claims"][0]
    claim["lens"] = "read_aloud"
    claim["audience"] = "PLAYER"
    with pytest.raises(CompositionError, match="player-safe"):
        project_card(contribution, context, audience="PLAYER", active_surface="Playing")
    claim["disclosure"] = "reviewed_player_safe"
    player = project_card(contribution, context, audience="PLAYER", active_surface="Playing")
    assert [c["id"] for c in player["lenses"]["read_aloud"]] == ["situation"]
