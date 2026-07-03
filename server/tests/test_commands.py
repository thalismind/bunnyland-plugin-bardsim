from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    NoiseComponent,
    PortableComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_bardsim import (
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
    spawn_lute,
    spawn_musician,
)
from bunnyland_bardsim.commands import LearnSongHandler, PerformHandler

SONG = "a merry harvest jig"


def _world_with_musician():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Tavern")])
    musician = spawn_musician(actor.world, name="Lira", room_id=room.id)
    return actor, room, musician


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=0)


def test_perform_spawns_an_audible_performance():
    actor, _room, musician = _world_with_musician()
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": str(lute.id), "song": SONG})
    )

    assert result.ok
    performances = list(
        actor.world.query().with_all([PerformanceNoiseComponent]).execute_entities()
    )
    assert len(performances) == 1
    noises = list(actor.world.query().with_all([NoiseComponent]).execute_entities())
    assert noises[0].get_component(NoiseComponent).text == SONG


def test_perform_reports_the_song_mood_on_its_event():
    actor, _room, musician = _world_with_musician()
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": str(lute.id), "song": SONG})
    )

    assert result.events[0].mood == "uplifting"


def test_perform_gives_a_tip_jar_to_a_performer_without_one():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Square")])
    performer = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Ash", kind="character"),
            CharacterComponent(),
            RepertoireComponent(songs=(SONG,)),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), performer.id)
    lute = spawn_lute(actor.world)
    _hold(performer, lute)

    PerformHandler().execute(
        _ctx(actor), _cmd(performer.id, "perform", {"item_id": str(lute.id), "song": SONG})
    )

    assert performer.has_component(TipJarComponent)


def test_perform_rejects_invalid_character_id():
    actor, _room, musician = _world_with_musician()
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    result = PerformHandler().execute(
        _ctx(actor), _cmd("???", "perform", {"item_id": str(lute.id), "song": SONG})
    )

    assert not result.ok
    assert result.reason == "invalid character id"


def test_perform_rejects_missing_item():
    actor, _room, musician = _world_with_musician()

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": "entity_9999", "song": SONG})
    )

    assert not result.ok
    assert result.reason == "item does not exist"


def test_perform_rejects_instrument_not_held():
    actor, room, musician = _world_with_musician()
    lute = spawn_lute(actor.world, room_id=room.id)  # on the floor, not held

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": str(lute.id), "song": SONG})
    )

    assert not result.ok
    assert result.reason == "you are not holding that instrument"


def test_perform_rejects_non_instrument_item():
    actor, _room, musician = _world_with_musician()
    mug = spawn_entity(
        actor.world,
        [IdentityComponent(name="mug", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(musician, mug)

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": str(mug.id), "song": SONG})
    )

    assert not result.ok
    assert result.reason == "that is not an instrument"


def test_perform_rejects_missing_song_argument():
    actor, _room, musician = _world_with_musician()
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    result = PerformHandler().execute(
        _ctx(actor), _cmd(musician.id, "perform", {"item_id": str(lute.id)})
    )

    assert not result.ok
    assert result.reason == "you need to name a song to perform"


def test_perform_rejects_unknown_song():
    actor, _room, musician = _world_with_musician()
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    result = PerformHandler().execute(
        _ctx(actor),
        _cmd(musician.id, "perform", {"item_id": str(lute.id), "song": "an unlearned tune"}),
    )

    assert not result.ok
    assert result.reason == "you do not know that song"


def test_learn_song_adds_to_repertoire():
    actor, _room, musician = _world_with_musician()

    result = LearnSongHandler().execute(
        _ctx(actor), _cmd(musician.id, "learn-song", {"song": "victory anthem"})
    )

    assert result.ok
    assert musician.get_component(RepertoireComponent).knows("victory anthem")


def test_learn_song_creates_a_repertoire_when_absent():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Road")])
    novice = spawn_entity(
        actor.world, [IdentityComponent(name="Pen", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), novice.id)

    result = LearnSongHandler().execute(
        _ctx(actor), _cmd(novice.id, "learn-song", {"song": "the road home"})
    )

    assert result.ok
    assert novice.get_component(RepertoireComponent).knows("the road home")


def test_learn_song_rejects_missing_song():
    actor, _room, musician = _world_with_musician()

    result = LearnSongHandler().execute(
        _ctx(actor), _cmd(musician.id, "learn-song", {"song": "   "})
    )

    assert not result.ok
    assert result.reason == "you need to name a song to learn"


def test_learn_song_rejects_already_known_song():
    actor, _room, musician = _world_with_musician()

    result = LearnSongHandler().execute(
        _ctx(actor), _cmd(musician.id, "learn-song", {"song": SONG})
    )

    assert not result.ok
    assert result.reason == "you already know that song"
