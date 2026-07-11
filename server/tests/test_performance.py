from __future__ import annotations

import pytest
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
from bunnyland.foundation.social.mechanics import adjust_bond

from bunnyland_bardsim import (
    PerformanceConsequence,
    TipJarComponent,
    spawn_lute,
    spawn_musician,
)
from bunnyland_bardsim.commands import PerformHandler
from bunnyland_bardsim.songs import MOOD_DELTAS, song_mood

EPOCH = 100
JIG = "a merry harvest jig"
LAMENT = "lament for the fallen"

#: One example song per mood, spanning the whole classified repertoire.
MOOD_SONGS = (
    "a joyful festival reel",  # uplifting
    "the iron battle march",  # rousing
    "a moonlight serenade for my beloved",  # romantic
    "the drunken jester's riddle",  # comic
    "the road home",  # wistful
    "lament for the fallen",  # somber
    "a haunting midnight air",  # eerie
    "a gentle cradle hush",  # lullaby
)


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


@pytest.mark.parametrize("song", MOOD_SONGS)
def test_each_song_mood_shifts_listener_valence_in_its_direction(song):
    # Every classified mood should move a listener's valence the way its delta promises,
    # end to end through perform -> noise -> consequence.
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Square")])
    performer = spawn_musician(actor.world, name="Lira", room_id=room.id, songs=(song,))
    lute = spawn_lute(actor.world)
    performer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), lute.id)
    listener = _listener(actor.world, room, "Bo")
    _perform(actor, performer, lute, song)

    PerformanceConsequence().process(actor.world, EPOCH)

    expected = MOOD_DELTAS[song_mood(song)].valence
    valence = listener.get_component(AffectComponent).current.valence
    if expected > 0:
        assert valence > 0
    elif expected < 0:
        assert valence < 0
    else:
        assert valence == 0


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
