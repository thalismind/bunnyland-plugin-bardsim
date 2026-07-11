"""Bunnyland plugin entrypoint for the out-of-tree bardsim music & performance extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
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
from .composing import (
    COMPOSE_SONG_DEF,
    Composed,
    ComposeSongHandler,
    CompositionComponent,
    SongComposedEvent,
    composition_fragments,
)
from .connectors import ContestEntryComponent, Reputation
from .enrichment import BardGenerationEnricher, BardGenerationNormalizer
from .ensembles import (
    FORM_ENSEMBLE_DEF,
    BandmateOf,
    EnsembleFormedEvent,
    FormEnsembleHandler,
    ensemble_fragments,
)
from .events import PerformedEvent, SongLearnedEvent
from .fragments import bardsim_fragments
from .install import install_bardsim
from .reputation import reputation_fragments
from .venues import (
    OPEN_VENUE_DEF,
    PERFORM_GIG_DEF,
    GigComponent,
    GigPerformedEvent,
    GigResolvedEvent,
    OpenVenueHandler,
    PerformGigHandler,
    VenueComponent,
    VenueOpenedEvent,
    venue_fragments,
)

PLUGIN_ID = "bunnyland.bardsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Bardsim",
        version="0.2.0",
        default_enabled=True,
        # Synergy partners are optional: bardsim runs standalone. A festival can host the
        # ContestEntry gigs publish; a museum can contribute donor renown; the storyteller
        # paces the fame incidents a famous act registers.
        dependencies=DependencyContribution(
            requires=("bunnyland.persona",),
            recommends=(
                "bunnyland.festivalsim",
                "bunnyland.museumsim",
                "bunnyland.storyteller",
            ),
        ),
        ecs=EcsContribution(
            components=(
                InstrumentComponent,
                RepertoireComponent,
                TipJarComponent,
                PerformanceNoiseComponent,
                VenueComponent,
                GigComponent,
                CompositionComponent,
                Reputation,
                ContestEntryComponent,
            ),
            edges=(BandmateOf, Composed),
        ),
        commands=CommandContribution(
            action_handlers=(
                *BARD_ACTION_HANDLERS,
                OpenVenueHandler,
                PerformGigHandler,
                FormEnsembleHandler,
                ComposeSongHandler,
            ),
            action_definitions=(
                *BARD_ACTION_DEFINITIONS,
                OPEN_VENUE_DEF,
                PERFORM_GIG_DEF,
                FORM_ENSEMBLE_DEF,
                COMPOSE_SONG_DEF,
            ),
            typed_events=(
                PerformedEvent,
                SongLearnedEvent,
                VenueOpenedEvent,
                GigPerformedEvent,
                GigResolvedEvent,
                EnsembleFormedEvent,
                SongComposedEvent,
            ),
        ),
        runtime=RuntimeContribution(service_factories=(install_bardsim,)),
        content=ContentContribution(
            prompt_fragments=(
                bardsim_fragments,
                venue_fragments,
                ensemble_fragments,
                composition_fragments,
                reputation_fragments,
            ),
            intent_normalizers=(BardGenerationNormalizer(),),
            generation_enrichers=(BardGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
