from __future__ import annotations

from bunnyland.mechanics.social import SocialBond

from bunnyland_bardsim.songs import (
    SOMBER,
    UPLIFTING,
    WISTFUL,
    mood_delta,
    song_mood,
    tip_for_listener,
)


def test_uplifting_song_is_classified():
    assert song_mood("a merry harvest jig") == UPLIFTING


def test_somber_song_is_classified():
    assert song_mood("lament for the fallen") == SOMBER


def test_neutral_song_reads_as_wistful():
    assert song_mood("the road home") == WISTFUL


def test_uplifting_terms_win_ties_with_somber_terms():
    # Contains both "farewell" (somber) and "dance" (uplifting): the crowd-pleaser wins.
    assert song_mood("a bright farewell dance") == UPLIFTING


def test_uplifting_mood_raises_valence():
    assert mood_delta("a merry harvest jig").valence > 0


def test_somber_mood_lowers_valence():
    assert mood_delta("lament for the fallen").valence < 0


def test_base_tip_without_a_bond():
    assert tip_for_listener(None) == 1


def test_fond_listener_tips_more():
    assert tip_for_listener(SocialBond(affinity=0.6, familiarity=0.3)) == 2


def test_indifferent_listener_tips_base():
    assert tip_for_listener(SocialBond(affinity=0.1)) == 1
