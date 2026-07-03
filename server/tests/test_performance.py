from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    NoiseComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.components import AffectComponent, PerceptionComponent
from bunnyland.core.consequences import HearingConsequence
from bunnyland.core.handlers import HandlerContext
from bunnyland.mechanics.social import adjust_bond

from bunnyland_bardsim import (
    PerformanceConsequence,
    TipJarComponent,
    spawn_lute,
    spawn_musician,
)
from bunnyland_bardsim.commands import PerformHandler

EPOCH = 100
JIG = "a merry harvest jig"
LAMENT = "lament for the fallen"


def _listener(world, room, name):
    character = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="character"),
            CharacterComponent(),
            AffectComponent(),
            PerceptionComponent(active=True),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _perform(actor, performer, lute, song):
    ctx = HandlerContext(world=actor.world, epoch=EPOCH)
    command = build_submitted_command(
        character_id=str(performer.id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="perform",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={"item_id": str(lute.id), "song": song},
    )
    return PerformHandler().execute(ctx, command)


def _stage(song=JIG):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Square")])
    performer = spawn_musician(actor.world, name="Lira", room_id=room.id)
    lute = spawn_lute(actor.world)
    performer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), lute.id)
    return actor, room, performer, lute


def test_uplifting_performance_lifts_listener_mood():
    actor, room, performer, lute = _stage(JIG)
    listener = _listener(actor.world, room, "Bo")
    _perform(actor, performer, lute, JIG)

    PerformanceConsequence().process(actor.world, EPOCH)

    assert listener.get_component(AffectComponent).current.valence > 0


def test_somber_performance_sinks_listener_mood():
    actor, room, performer, lute = _stage(LAMENT)
    listener = _listener(actor.world, room, "Bo")
    _perform(actor, performer, lute, LAMENT)

    PerformanceConsequence().process(actor.world, EPOCH)

    assert listener.get_component(AffectComponent).current.valence < 0


def test_tips_scale_with_audience_size():
    actor, room, performer, lute = _stage(JIG)
    _listener(actor.world, room, "Bo")
    _listener(actor.world, room, "Cy")
    _perform(actor, performer, lute, JIG)

    PerformanceConsequence().process(actor.world, EPOCH)

    assert performer.get_component(TipJarComponent).coins == 2


def test_a_fond_listener_tips_extra():
    actor, room, performer, lute = _stage(JIG)
    fan = _listener(actor.world, room, "Bo")
    adjust_bond(actor.world, fan.id, performer.id, {"affinity": 0.6, "familiarity": 0.3})
    _perform(actor, performer, lute, JIG)

    PerformanceConsequence().process(actor.world, EPOCH)

    assert performer.get_component(TipJarComponent).coins == 2


def test_performer_is_not_their_own_audience():
    actor, room, performer, lute = _stage(JIG)
    # No listeners at all: the performer should not tip or shift their own (absent) mood.
    _perform(actor, performer, lute, JIG)

    PerformanceConsequence().process(actor.world, EPOCH)

    assert performer.get_component(TipJarComponent).coins == 0


def test_performance_resolves_only_once_across_ticks():
    actor, room, performer, lute = _stage(JIG)
    _listener(actor.world, room, "Bo")
    _perform(actor, performer, lute, JIG)
    consequence = PerformanceConsequence()

    consequence.process(actor.world, EPOCH)
    consequence.process(actor.world, EPOCH + 1)  # noise still alive, must not pay twice

    assert performer.get_component(TipJarComponent).coins == 1


def test_performance_is_audible_through_core_hearing():
    actor, room, performer, lute = _stage(JIG)
    listener = _listener(actor.world, room, "Bo")
    _perform(actor, performer, lute, JIG)

    events = HearingConsequence().process(actor.world, EPOCH)

    assert any(getattr(event, "text", "") == JIG for event in events)
    assert listener.get_component(PerceptionComponent).audible_entities


def test_process_ignores_stray_noise_without_a_performance():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Void")])
    spawn_entity(
        actor.world,
        [
            NoiseComponent(
                loudness=3.0, text="clatter", room_id=str(room.id), expires_at_epoch=EPOCH + 10
            )
        ],
    )

    # No PerformanceNoiseComponent present: the consequence has nothing to resolve.
    assert PerformanceConsequence().process(actor.world, EPOCH) == []
