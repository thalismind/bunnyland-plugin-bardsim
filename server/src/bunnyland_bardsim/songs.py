"""Song mood classification and tip math.

A song is just a free-text title a character has learned. Its *mood* is derived
deterministically from keywords in that title, and the mood maps to an :class:`AffectDelta`
applied to everyone who hears it. Keeping the mapping keyword-driven means learned songs
need no registry: ``"a merry harvest jig"`` reads as uplifting, ``"lament for the fallen"``
reads as somber, and anything else is wistful.

Tip amounts are likewise a pure function of the audience's social bonds, so a performance's
payout is fully reproducible from world state.
"""

from __future__ import annotations

from bunnyland.core.components import AffectDelta
from bunnyland.mechanics.social import SocialBond

UPLIFTING = "uplifting"
SOMBER = "somber"
WISTFUL = "wistful"

#: Moods in a stable order (handy for tests and iteration).
MOODS = (UPLIFTING, SOMBER, WISTFUL)

#: Title keywords that read as an uplifting, crowd-pleasing tune.
UPLIFTING_TERMS = (
    "jig",
    "reel",
    "anthem",
    "victory",
    "triumph",
    "sunrise",
    "dawn",
    "dance",
    "merry",
    "joy",
    "joyful",
    "bright",
    "festival",
    "celebration",
    "harvest",
    "wedding",
    "hymn",
)

#: Title keywords that read as a somber, mournful tune.
SOMBER_TERMS = (
    "lament",
    "dirge",
    "elegy",
    "requiem",
    "farewell",
    "sorrow",
    "sorrowful",
    "mourning",
    "mournful",
    "funeral",
    "grief",
    "fallen",
    "lost",
    "lonely",
    "winter",
)

#: Per-mood affect shift applied to each listener when a performance is heard.
MOOD_DELTAS: dict[str, AffectDelta] = {
    UPLIFTING: AffectDelta(valence=8.0, stress=-5.0, sociability=4.0),
    SOMBER: AffectDelta(valence=-4.0, sadness=6.0, arousal=-2.0),
    WISTFUL: AffectDelta(valence=2.0, sadness=2.0, focus=2.0),
}


def song_mood(song: str) -> str:
    """Classify a song title into one of :data:`MOODS` from its keywords.

    Uplifting terms win ties with somber ones so a "bright farewell dance" still lands as a
    crowd-pleaser; a title with neither reads as wistful.
    """
    text = song.casefold()
    if any(term in text for term in UPLIFTING_TERMS):
        return UPLIFTING
    if any(term in text for term in SOMBER_TERMS):
        return SOMBER
    return WISTFUL


def mood_delta(song: str) -> AffectDelta:
    """Return the :class:`AffectDelta` a performance of ``song`` applies to listeners."""
    return MOOD_DELTAS[song_mood(song)]


def tip_for_listener(bond: SocialBond | None) -> int:
    """Coins a single listener tips a performer.

    Everyone tosses a base coin; a listener who already likes or knows the performer
    (positive affinity + familiarity) tips one more. Bond fields are clamped to ``[-1, 1]``,
    so the payout stays small and deterministic.
    """
    base = 1
    if bond is not None and (bond.affinity + bond.familiarity) >= 0.5:
        return base + 1
    return base


__all__ = [
    "MOODS",
    "MOOD_DELTAS",
    "SOMBER",
    "SOMBER_TERMS",
    "UPLIFTING",
    "UPLIFTING_TERMS",
    "WISTFUL",
    "mood_delta",
    "song_mood",
    "tip_for_listener",
]
