"""Bunnyland plugin entrypoint for the out-of-tree bardsim music & performance extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import BARD_ACTION_DEFINITIONS, BARD_ACTION_HANDLERS
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

PLUGIN_ID = "bunnyland.bardsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Bardsim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                InstrumentComponent,
                RepertoireComponent,
                TipJarComponent,
                PerformanceNoiseComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=BARD_ACTION_HANDLERS,
            action_definitions=BARD_ACTION_DEFINITIONS,
            typed_events=(PerformedEvent, SongLearnedEvent),
        ),
        runtime=RuntimeContribution(service_factories=(install_bardsim,)),
        content=ContentContribution(
            prompt_fragments=(bardsim_fragments,),
            worldgen_hooks=(BardWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
