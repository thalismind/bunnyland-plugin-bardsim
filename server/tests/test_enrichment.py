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
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_bardsim import InstrumentComponent, RepertoireComponent, TipJarComponent


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
