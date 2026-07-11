from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.foundation.persona.plugin import plugin as persona_plugin
from bunnyland.plugins import apply_plugins

from bunnyland_bardsim import (
    BandmateOf,
    BardGenerationEnricher,
    Composed,
    CompositionComponent,
    ContestEntryComponent,
    GigComponent,
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    Reputation,
    TipJarComponent,
    VenueComponent,
    bardsim_fragments,
    composition_fragments,
    ensemble_fragments,
    reputation_fragments,
    venue_fragments,
)
from bunnyland_bardsim.plugin import PLUGIN_ID
from bunnyland_bardsim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_module_qualified_id():
    plugins = _plugins()
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = _plugins()[0]
    for component in (
        InstrumentComponent,
        RepertoireComponent,
        TipJarComponent,
        PerformanceNoiseComponent,
    ):
        assert component in plugin.ecs.components
    assert BardGenerationEnricher in [type(item) for item in plugin.content.generation_enrichers]
    assert bardsim_fragments in plugin.content.prompt_fragments


def test_plugin_declares_v2_surfaces():
    plugin = _plugins()[0]
    for component in (
        VenueComponent,
        GigComponent,
        CompositionComponent,
        Reputation,
        ContestEntryComponent,
    ):
        assert component in plugin.ecs.components
    # Relationships are typed edges, one index each -- never a list on a component.
    assert BandmateOf in plugin.ecs.edges
    assert Composed in plugin.ecs.edges
    for provider in (
        venue_fragments,
        ensemble_fragments,
        composition_fragments,
        reputation_fragments,
    ):
        assert provider in plugin.content.prompt_fragments


def test_plugin_recommends_optional_partners_and_requires_persona():
    plugin = _plugins()[0]
    recommends = set(plugin.dependencies.recommends)
    assert {"bunnyland.festivalsim", "bunnyland.museumsim", "bunnyland.storyteller"} <= recommends
    assert plugin.dependencies.requires == ("bunnyland.persona",)


def test_plugin_version_is_bumped():
    plugin = _plugins()[0]
    assert plugin.version == "0.2.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins([persona_plugin(), *_plugins()], actor)
    assert applied[-1].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "perform",
        "learn-song",
        "open-venue",
        "perform-gig",
        "form-ensemble",
        "compose-song",
    } <= command_types
