from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    IdentityComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import CharacterGeneratedEvent, ObjectGeneratedEvent, event_base
from bunnyland.mechanics.persona import GoalComponent
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_bardsim import InstrumentComponent, RepertoireComponent, TipJarComponent
from bunnyland_bardsim.enrichment import BardWorldgenHook
from bunnyland_bardsim.reputation import RENOWNED_GOAL


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_bardsim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _character(actor, *, tags=(), description=""):
    entity = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    event = CharacterGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="npc",
        entity_kind="character",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        character_key="npc",
        room_id="room_1",
    )
    _publish(actor, event)
    return entity


def _object(actor, *, tags=(), description=""):
    entity = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="thing",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        object_key="thing",
    )
    _publish(actor, event)
    return entity


def test_musician_character_gets_a_repertoire():
    actor = _actor()
    bard = _character(actor, tags=("bard", "musician"))
    assert bard.has_component(RepertoireComponent)
    assert bard.get_component(RepertoireComponent).songs
    assert bard.has_component(TipJarComponent)


def test_musician_detected_from_description_text():
    actor = _actor()
    bard = _character(actor, description="a wandering minstrel with a warm voice")
    assert bard.has_component(RepertoireComponent)


def test_non_musician_character_is_not_marked():
    actor = _actor()
    farmer = _character(actor, tags=("farmer",), description="a weathered field hand")
    assert not farmer.has_component(RepertoireComponent)


def test_instrument_object_gets_instrument_component_with_inferred_kind():
    actor = _actor()
    fiddle = _object(actor, tags=("fiddle", "wooden"))
    assert fiddle.has_component(InstrumentComponent)
    assert fiddle.get_component(InstrumentComponent).kind == "fiddle"


def test_generic_instrument_defaults_to_lute():
    actor = _actor()
    thing = _object(actor, description="a stringed musical instrument")
    assert thing.get_component(InstrumentComponent).kind == "lute"


def test_plain_object_is_not_marked():
    actor = _actor()
    crate = _object(actor, tags=("wooden", "storage"))
    assert not crate.has_component(InstrumentComponent)


def test_generated_musician_aspires_to_renown_via_core_goals():
    actor = _actor()
    bard = _character(actor, tags=("bard",))
    # The fame ambition routes through the core persona/goals surface, not a bardsim field.
    assert RENOWNED_GOAL in bard.get_component(GoalComponent).active_goals


def test_worldgen_hook_is_idempotent_on_reruns():
    actor = _actor()
    # A musician re-run must not re-seed a repertoire or a second tip jar.
    bard = _character(actor, tags=("bard",))
    songs = bard.get_component(RepertoireComponent).songs
    _character_rerun = CharacterGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(bard.id),
        entity_key="npc",
        entity_kind="character",
        generation=GenerationIntentComponent(tags=("bard",)),
        character_key="npc",
        room_id="room_1",
    )
    _publish(actor, _character_rerun)
    assert bard.get_component(RepertoireComponent).songs == songs

    # An instrument re-run keeps its first inferred kind.
    fiddle = _object(actor, tags=("fiddle",))
    _object_rerun = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(fiddle.id),
        entity_key="thing",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=("drum",)),  # would-be new kind, ignored
        object_key="thing",
    )
    _publish(actor, _object_rerun)
    assert fiddle.get_component(InstrumentComponent).kind == "fiddle"


def test_worldgen_hook_ignores_events_for_missing_entities():
    actor = _actor()
    hook = BardWorldgenHook()
    hook.subscribe(actor)
    ghost_char = CharacterGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id="ghost_777",
        entity_key="npc",
        entity_kind="character",
        generation=GenerationIntentComponent(tags=("bard",)),
        character_key="npc",
        room_id="room_1",
    )
    ghost_obj = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id="ghost_888",
        entity_key="thing",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=("fiddle",)),
        object_key="thing",
    )
    # No entity behind the id -> the hook simply does nothing (no crash).
    hook._on_character(ghost_char)
    hook._on_object(ghost_obj)
    assert hook._entity("ghost_777") is None
    assert hook._entity("not-an-id") is None
