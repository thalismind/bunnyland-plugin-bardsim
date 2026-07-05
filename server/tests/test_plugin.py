from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_bardsim import (
    BandmateOf,
    BardWorldgenHook,
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


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_bardsim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_bardsim"])[0]
    for component in (
        InstrumentComponent,
        RepertoireComponent,
        TipJarComponent,
        PerformanceNoiseComponent,
    ):
        assert component in plugin.ecs.components
    assert BardWorldgenHook in plugin.content.worldgen_hooks
    assert bardsim_fragments in plugin.content.prompt_fragments


def test_plugin_declares_v2_surfaces():
    plugin = load_modules(["bunnyland_bardsim"])[0]
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


def test_plugin_recommends_optional_partners_but_requires_none():
    plugin = load_modules(["bunnyland_bardsim"])[0]
    recommends = set(plugin.dependencies.recommends)
    assert {"bunnyland.festivalsim", "bunnyland.museumsim", "bunnyland.storyteller"} <= recommends
    assert not plugin.dependencies.requires  # bardsim runs standalone


def test_plugin_version_is_bumped():
    plugin = load_modules(["bunnyland_bardsim"])[0]
    assert plugin.version == "0.2.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_bardsim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "perform",
        "learn-song",
        "open-venue",
        "perform-gig",
        "form-ensemble",
        "compose-song",
    } <= command_types
