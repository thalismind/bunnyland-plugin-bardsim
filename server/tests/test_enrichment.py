import asyncio

from bunnyland.core import WorldActor
from bunnyland.foundation.persona.mechanics import GoalComponent
from bunnyland.foundation.persona.plugin import plugin as persona_plugin
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import CharacterSpec, ObjectSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_bardsim import InstrumentComponent, RepertoireComponent, TipJarComponent
from bunnyland_bardsim.plugin import bunnyland_plugins as _plugins
from bunnyland_bardsim.reputation import RENOWNED_GOAL


def _world(*, character=None, object_=None):
    actor = WorldActor()
    apply_plugins([persona_plugin(), *_plugins()], actor)
    proposal = WorldProposal(
        seed="seed",
        rooms=[RoomSpec(key="room", title="Room")],
        characters=[character] if character else [],
        objects=[object_] if object_ else [],
    )
    result = asyncio.run(instantiate(actor, proposal))
    return actor, result


def test_musician_gets_repertoire_tip_jar_and_persona_goal():
    actor, result = _world(
        character=CharacterSpec(key="bard", name="Bard", room_key="room", traits=("musician",))
    )
    bard = actor.world.get_entity(result.characters["bard"])
    assert bard.get_component(RepertoireComponent).songs
    assert bard.has_component(TipJarComponent)
    assert RENOWNED_GOAL in bard.get_component(GoalComponent).active_goals


def test_musician_detected_from_description_and_non_musician_ignored():
    actor, result = _world(
        character=CharacterSpec(
            key="minstrel",
            name="Traveler",
            room_key="room",
            description="a wandering minstrel",
        )
    )
    assert actor.world.get_entity(result.characters["minstrel"]).has_component(RepertoireComponent)
    actor, result = _world(character=CharacterSpec(key="farmer", name="Farmer", room_key="room"))
    assert not actor.world.get_entity(result.characters["farmer"]).has_component(
        RepertoireComponent
    )


def test_instruments_are_inferred_and_plain_objects_ignored():
    actor, result = _world(
        object_=ObjectSpec(key="fiddle", name="Fiddle", room_key="room", tags=("wooden",))
    )
    assert (
        actor.world.get_entity(result.objects["fiddle"]).get_component(InstrumentComponent).kind
        == "fiddle"
    )
    actor, result = _world(
        object_=ObjectSpec(
            key="music", name="Music thing", room_key="room", description="an instrument"
        )
    )
    assert (
        actor.world.get_entity(result.objects["music"]).get_component(InstrumentComponent).kind
        == "lute"
    )
    actor, result = _world(object_=ObjectSpec(key="crate", name="Crate", room_key="room"))
    assert not actor.world.get_entity(result.objects["crate"]).has_component(InstrumentComponent)
