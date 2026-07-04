"""Song mood classification and tip math.

A song is just a free-text title a character has learned. Its *mood* is derived
deterministically from keywords in that title, and the mood maps to an :class:`AffectDelta`
applied to everyone who hears it. Keeping the mapping keyword-driven means learned songs
need no registry: ``"a merry harvest jig"`` reads as uplifting, ``"lament for the fallen"``
reads as somber, ``"a haunting midnight air"`` reads as eerie, and anything with no telling
keyword reads as wistful.

Classification is a single ordered pass over :data:`CLASSIFICATION_ORDER`: the first mood
whose keyword list matches wins, so priority is explicit and reproducible. Uplifting sits
first, keeping the historical rule that a "bright farewell dance" lands as a crowd-pleaser
rather than a dirge.

Tip amounts are likewise a pure function of the audience's social bonds, so a performance's
payout is fully reproducible from world state.
"""

from __future__ import annotations

from bunnyland.core.components import AffectDelta
from bunnyland.mechanics.social import SocialBond

UPLIFTING = "uplifting"
ROUSING = "rousing"
ROMANTIC = "romantic"
COMIC = "comic"
WISTFUL = "wistful"
SOMBER = "somber"
EERIE = "eerie"
LULLABY = "lullaby"

#: Moods in a stable order (handy for tests and iteration).
MOODS = (UPLIFTING, ROUSING, ROMANTIC, COMIC, WISTFUL, SOMBER, EERIE, LULLABY)

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
    "spring",
    "bloom",
    "cheer",
    "sunny",
)

#: Title keywords that read as a bold, blood-stirring call to action.
ROUSING_TERMS = (
    "march",
    "battle",
    "war",
    "warcry",
    "rally",
    "charge",
    "thunder",
    "storm",
    "forge",
    "bold",
    "courage",
    "valor",
    "banner",
    "hero",
    "uprising",
    "rebellion",
    "conquest",
    "iron",
)

#: Title keywords that read as a tender, amorous serenade.
ROMANTIC_TERMS = (
    "love",
    "serenade",
    "sweetheart",
    "rose",
    "kiss",
    "beloved",
    "valentine",
    "heart",
    "courtship",
    "moonlight",
    "embrace",
    "darling",
    "romance",
    "sweet",
)

#: Title keywords that read as a silly, laugh-chasing romp.
COMIC_TERMS = (
    "silly",
    "jest",
    "jester",
    "comic",
    "clown",
    "drunken",
    "tavern",
    "riddle",
    "nonsense",
    "tipsy",
    "bawdy",
    "limerick",
    "folly",
    "prank",
    "fool",
    "giggle",
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
    "tears",
    "weeping",
    "ashes",
    "ruin",
)

#: Title keywords that read as an unsettling, spine-tingling air.
EERIE_TERMS = (
    "haunt",
    "haunting",
    "ghost",
    "ghostly",
    "specter",
    "spectral",
    "shadow",
    "eerie",
    "wraith",
    "phantom",
    "cursed",
    "midnight",
    "hollow",
    "crypt",
    "tomb",
    "grave",
    "banshee",
    "macabre",
    "witching",
)

#: Title keywords that read as a soft, sleep-inducing cradle song.
LULLABY_TERMS = (
    "lullaby",
    "cradle",
    "sleep",
    "hush",
    "slumber",
    "dream",
    "gentle",
    "drowsy",
    "nightfall",
    "whisper",
    "soft",
    "peaceful",
)

#: Keyword lists per mood. ``WISTFUL`` is the fallback mood and has no keywords.
MOOD_TERMS: dict[str, tuple[str, ...]] = {
    UPLIFTING: UPLIFTING_TERMS,
    ROUSING: ROUSING_TERMS,
    ROMANTIC: ROMANTIC_TERMS,
    COMIC: COMIC_TERMS,
    SOMBER: SOMBER_TERMS,
    EERIE: EERIE_TERMS,
    LULLABY: LULLABY_TERMS,
}

#: The order keyword lists are consulted; the first match wins. Uplifting leads so a
#: crowd-pleaser beats a mournful keyword in the same title.
CLASSIFICATION_ORDER = (UPLIFTING, ROUSING, ROMANTIC, COMIC, EERIE, LULLABY, SOMBER)

#: Per-mood affect shift applied to each listener when a performance is heard.
MOOD_DELTAS: dict[str, AffectDelta] = {
    UPLIFTING: AffectDelta(valence=8.0, stress=-5.0, sociability=4.0),
    ROUSING: AffectDelta(valence=5.0, arousal=6.0, confidence=5.0, stress=-3.0),
    ROMANTIC: AffectDelta(valence=6.0, sociability=5.0, arousal=2.0, sadness=-2.0),
    COMIC: AffectDelta(valence=7.0, stress=-6.0, arousal=3.0, sociability=5.0),
    WISTFUL: AffectDelta(valence=2.0, sadness=2.0, focus=2.0),
    SOMBER: AffectDelta(valence=-4.0, sadness=6.0, arousal=-2.0),
    EERIE: AffectDelta(valence=-2.0, fear=5.0, arousal=4.0, curiosity=3.0),
    LULLABY: AffectDelta(valence=3.0, stress=-6.0, arousal=-6.0, focus=1.0),
}


def song_mood(song: str) -> str:
    """Classify a song title into one of :data:`MOODS` from its keywords.

    Keyword lists are consulted in :data:`CLASSIFICATION_ORDER`, so uplifting terms win ties
    with any later mood: a "bright farewell dance" still lands as a crowd-pleaser. A title
    with no telling keyword reads as wistful.
    """
    text = song.casefold()
    for mood in CLASSIFICATION_ORDER:
        if any(term in text for term in MOOD_TERMS[mood]):
            return mood
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
    "CLASSIFICATION_ORDER",
    "COMIC",
    "COMIC_TERMS",
    "EERIE",
    "EERIE_TERMS",
    "LULLABY",
    "LULLABY_TERMS",
    "MOODS",
    "MOOD_DELTAS",
    "MOOD_TERMS",
    "ROMANTIC",
    "ROMANTIC_TERMS",
    "ROUSING",
    "ROUSING_TERMS",
    "SOMBER",
    "SOMBER_TERMS",
    "UPLIFTING",
    "UPLIFTING_TERMS",
    "WISTFUL",
    "mood_delta",
    "song_mood",
    "tip_for_listener",
]
