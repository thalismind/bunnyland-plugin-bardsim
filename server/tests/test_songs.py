from __future__ import annotations

import pytest
from bunnyland.mechanics.social import SocialBond

from bunnyland_bardsim.songs import (
    COMIC,
    EERIE,
    LULLABY,
    MOOD_DELTAS,
    MOODS,
    ROMANTIC,
    ROUSING,
    SOMBER,
    UPLIFTING,
    WISTFUL,
    mood_delta,
    song_mood,
    tip_for_listener,
)

#: One unambiguous example title per mood, used to exercise classification and deltas.
MOOD_EXAMPLES = (
    (UPLIFTING, "a joyful festival reel"),
    (ROUSING, "the iron battle march"),
    (ROMANTIC, "a moonlight serenade for my beloved"),
    (COMIC, "the drunken jester's riddle"),
    (WISTFUL, "the road home"),
    (SOMBER, "lament for the fallen"),
    (EERIE, "a haunting midnight air"),
    (LULLABY, "a gentle cradle hush"),
)


@pytest.mark.parametrize("mood,title", MOOD_EXAMPLES)
def test_song_titles_classify_to_their_mood(mood, title):
    assert song_mood(title) == mood


def test_every_mood_has_a_worked_example():
    # Guard the table: it should cover the full, stable mood roster exactly once.
    assert {mood for mood, _ in MOOD_EXAMPLES} == set(MOODS)
    assert len(MOOD_EXAMPLES) == len(MOODS)


@pytest.mark.parametrize("mood", MOODS)
def test_every_mood_maps_to_a_delta(mood):
    assert mood in MOOD_DELTAS


@pytest.mark.parametrize("mood,title", MOOD_EXAMPLES)
def test_mood_delta_matches_song_mood(mood, title):
    assert mood_delta(title) == MOOD_DELTAS[mood]


def test_uplifting_song_is_classified():
    assert song_mood("a merry harvest jig") == UPLIFTING


def test_somber_song_is_classified():
    assert song_mood("lament for the fallen") == SOMBER


def test_neutral_song_reads_as_wistful():
    assert song_mood("the road home") == WISTFUL


def test_uplifting_terms_win_ties_with_somber_terms():
    # Contains both "farewell" (somber) and "dance" (uplifting): the crowd-pleaser wins.
    assert song_mood("a bright farewell dance") == UPLIFTING


def test_eerie_wins_over_a_later_somber_keyword():
    # "dirge" (somber) sits after "eerie" in the classification order, so the ghostly
    # keyword decides the mood.
    assert song_mood("an eerie funeral dirge") == EERIE


def test_uplifting_mood_raises_valence():
    assert mood_delta("a merry harvest jig").valence > 0


def test_somber_mood_lowers_valence():
    assert mood_delta("lament for the fallen").valence < 0


def test_rousing_mood_raises_arousal_and_confidence():
    delta = mood_delta("the iron battle march")
    assert delta.arousal > 0 and delta.confidence > 0


def test_eerie_mood_stirs_fear():
    assert mood_delta("a haunting midnight air").fear > 0


def test_lullaby_mood_calms_arousal():
    assert mood_delta("a gentle cradle hush").arousal < 0


def test_base_tip_without_a_bond():
    assert tip_for_listener(None) == 1


def test_fond_listener_tips_more():
    assert tip_for_listener(SocialBond(affinity=0.6, familiarity=0.3)) == 2


def test_indifferent_listener_tips_base():
    assert tip_for_listener(SocialBond(affinity=0.1)) == 1
