from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component

from bunnyland_bardsim import (
    PerformanceNoiseComponent,
    RepertoireComponent,
    bardsim_fragments,
    spawn_lute,
)


def _room(world):
    return spawn_entity(world, [RoomComponent(title="Green")])


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _perform_in(world, room, performer, song):
    spawn_entity(
        world,
        [
            PerformanceNoiseComponent(
                song=song,
                mood="uplifting",
                performer_id=str(performer.id),
                performer_name=performer.get_component(IdentityComponent).name,
                room_id=str(room.id),
            )
        ],
    )


def test_holder_reads_first_person_instrument_line():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room, "Vin")
    lute = spawn_lute(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), lute.id)

    assert bardsim_fragments(actor.world, holder) == ["You are holding a lute."]


def test_bystander_reads_third_person_line_for_floor_instrument():
    actor = WorldActor()
    room = _room(actor.world)
    bystander = _character(actor.world, room, "Kell")
    spawn_lute(actor.world, room_id=room.id)  # on the floor

    assert bardsim_fragments(actor.world, bystander) == ["A lute rests here."]


def test_first_person_sees_own_repertoire():
    actor = WorldActor()
    room = _room(actor.world)
    bard = _character(actor.world, room, "Lira")
    replace_component(bard, RepertoireComponent(songs=("the road home", "a merry harvest jig")))

    assert bardsim_fragments(actor.world, bard) == [
        "You know how to play: a merry harvest jig, the road home."
    ]


def test_bystander_hears_what_is_playing():
    actor = WorldActor()
    room = _room(actor.world)
    performer = _character(actor.world, room, "Lira")
    audience = _character(actor.world, room, "Kell")
    _perform_in(actor.world, room, performer, "a merry harvest jig")

    assert bardsim_fragments(actor.world, audience) == [
        'Lira is playing "a merry harvest jig" here.'
    ]


def test_performer_reads_first_person_playing_line():
    actor = WorldActor()
    room = _room(actor.world)
    performer = _character(actor.world, room, "Lira")
    _perform_in(actor.world, room, performer, "a merry harvest jig")

    assert bardsim_fragments(actor.world, performer) == [
        'You are playing "a merry harvest jig" here.'
    ]


def test_quiet_empty_room_has_no_fragments():
    actor = WorldActor()
    room = _room(actor.world)
    loiterer = _character(actor.world, room, "Kell")

    assert bardsim_fragments(actor.world, loiterer) == []
