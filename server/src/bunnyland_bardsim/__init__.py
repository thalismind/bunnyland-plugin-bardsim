"""Out-of-tree Bunnyland plugin: a music & performance pack (instruments, songs, busking).

v2 adds venues & gigs, ensembles (a typed ``BandmateOf`` edge), composing (a typed
``Composed`` edge), and a shared ``Reputation`` connector surface, wiring core affect,
social, persona/goals, and the storyteller (a famous act draws a crowd).
"""

from .commands import LearnSongHandler, PerformHandler
from .components import (
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
)
from .composing import (
    COMPOSE_RENOWN,
    Composed,
    ComposeSongHandler,
    CompositionComponent,
    SongComposedEvent,
    composition_fragments,
    compositions_of,
)
from .connectors import (
    ContestEntryComponent,
    Reputation,
    contest_entries,
    external_reputation_bonus,
)
from .enrichment import BardWorldgenHook
from .ensembles import (
    BandmateOf,
    EnsembleFormedEvent,
    FormEnsembleHandler,
    are_bandmates,
    bandmates_of,
    ensemble_fragments,
    present_bandmates,
)
from .events import PerformedEvent, SongLearnedEvent
from .fragments import bardsim_fragments
from .install import install_bardsim
from .performance import PerformanceConsequence
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import (
    INSTRUMENT_FAMILIES,
    INSTRUMENT_KINDS,
    INSTRUMENT_SPAWNERS,
    spawn_drum,
    spawn_fiddle,
    spawn_instrument,
    spawn_lute,
    spawn_musician,
)
from .reputation import (
    FAME_THRESHOLD,
    RENOWNED_GOAL,
    aspire_to_renown,
    grant_renown,
    is_famous,
    reputation_fragments,
    reputation_of,
    standing,
)
from .songs import MOODS, mood_delta, song_mood, tip_for_listener
from .spatial import holder_of, room_of
from .venues import (
    GigComponent,
    GigConsequence,
    GigPerformedEvent,
    GigResolvedEvent,
    OpenVenueHandler,
    PerformGigHandler,
    VenueComponent,
    VenueOpenedEvent,
    venue_fragments,
)

__all__ = [
    "COMPOSE_RENOWN",
    "FAME_THRESHOLD",
    "INSTRUMENT_FAMILIES",
    "INSTRUMENT_KINDS",
    "INSTRUMENT_SPAWNERS",
    "MOODS",
    "PLUGIN_ID",
    "RENOWNED_GOAL",
    "BandmateOf",
    "BardWorldgenHook",
    "Composed",
    "ComposeSongHandler",
    "CompositionComponent",
    "ContestEntryComponent",
    "EnsembleFormedEvent",
    "FormEnsembleHandler",
    "GigComponent",
    "GigConsequence",
    "GigPerformedEvent",
    "GigResolvedEvent",
    "InstrumentComponent",
    "LearnSongHandler",
    "OpenVenueHandler",
    "PerformGigHandler",
    "PerformHandler",
    "PerformanceConsequence",
    "PerformanceNoiseComponent",
    "PerformedEvent",
    "RepertoireComponent",
    "Reputation",
    "SongComposedEvent",
    "SongLearnedEvent",
    "TipJarComponent",
    "VenueComponent",
    "VenueOpenedEvent",
    "are_bandmates",
    "aspire_to_renown",
    "bandmates_of",
    "bardsim_fragments",
    "bunnyland_plugins",
    "composition_fragments",
    "compositions_of",
    "contest_entries",
    "ensemble_fragments",
    "external_reputation_bonus",
    "grant_renown",
    "holder_of",
    "install_bardsim",
    "is_famous",
    "mood_delta",
    "plugin",
    "present_bandmates",
    "reputation_fragments",
    "reputation_of",
    "room_of",
    "song_mood",
    "spawn_drum",
    "spawn_fiddle",
    "spawn_instrument",
    "spawn_lute",
    "spawn_musician",
    "standing",
    "tip_for_listener",
    "venue_fragments",
]
