"""Out-of-tree Bunnyland plugin: a music & performance pack (instruments, songs, busking)."""

from .commands import LearnSongHandler, PerformHandler
from .components import (
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
)
from .enrichment import BardWorldgenHook
from .events import PerformedEvent, SongLearnedEvent
from .fragments import bardsim_fragments
from .install import install_bardsim
from .performance import PerformanceConsequence
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_drum, spawn_fiddle, spawn_lute, spawn_musician
from .songs import mood_delta, song_mood, tip_for_listener
from .spatial import holder_of, room_of

__all__ = [
    "PLUGIN_ID",
    "BardWorldgenHook",
    "InstrumentComponent",
    "LearnSongHandler",
    "PerformHandler",
    "PerformanceConsequence",
    "PerformanceNoiseComponent",
    "PerformedEvent",
    "RepertoireComponent",
    "SongLearnedEvent",
    "TipJarComponent",
    "bardsim_fragments",
    "bunnyland_plugins",
    "holder_of",
    "install_bardsim",
    "mood_delta",
    "plugin",
    "room_of",
    "song_mood",
    "spawn_drum",
    "spawn_fiddle",
    "spawn_lute",
    "spawn_musician",
    "tip_for_listener",
]
