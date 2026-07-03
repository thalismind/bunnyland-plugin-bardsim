from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_bardsim import (
    BardWorldgenHook,
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
    bardsim_fragments,
)
from bunnyland_bardsim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_bardsim"])
    assert [p.id for p in plugins] == [f"bunnyland_bardsim.{PLUGIN_ID}"]


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


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_bardsim"]), actor)
    assert applied[0].id == f"bunnyland_bardsim.{PLUGIN_ID}"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"perform", "learn-song"} <= command_types
