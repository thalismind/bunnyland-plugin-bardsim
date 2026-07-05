"""Guard-path and edge-case coverage for bardsim: consequence guards, fragments, spatial,
the optional museum synergy, and v1 rejection corners the v2 wiring newly exposes."""

from __future__ import annotations

import sys
import types

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
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.handlers import HandlerContext
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

from bunnyland_bardsim.components import PerformanceNoiseComponent, RepertoireComponent
from bunnyland_bardsim.connectors import external_reputation_bonus
from bunnyland_bardsim.fragments import bardsim_fragments
from bunnyland_bardsim.performance import PerformanceConsequence
from bunnyland_bardsim.prefabs import spawn_lute, spawn_musician
from bunnyland_bardsim.spatial import holder_of, room_of
from bunnyland_bardsim.venues import (
    GigComponent,
    GigConsequence,
    GigResolvedEvent,
)


def _room(world, title="Tavern"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _place(world, room, entity):
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload=None):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload or {},
    )


def _ghost():
    return parse_entity_id("ghost_999")


# --------------------------------------------------------------------------------------
# GigConsequence guard paths
# --------------------------------------------------------------------------------------


def test_gig_scoring_skips_a_gig_whose_room_is_gone():
    actor = WorldActor()
    spawn_entity(
        actor.world,
        [
            GigComponent(
                performer_id="ghost_1",
                performer_name="Ghost",
                song="a tune",
                mood="wistful",
                venue_id="ghost_2",
                venue_name="Nowhere",
                prestige=1,
                room_id="ghost_2",
            )
        ],
    )
    assert GigConsequence().process(actor.world, 5) == []


def test_gig_scoring_tolerates_a_departed_performer():
    actor = WorldActor()
    room = _room(actor.world)
    # A gig whose room still exists but whose performer entity has despawned.
    spawn_entity(
        actor.world,
        [
            GigComponent(
                performer_id="ghost_1",
                performer_name="Ghost",
                song="a tune",
                mood="wistful",
                venue_id=str(room.id),
                venue_name="The Rest",
                prestige=1,
                room_id=str(room.id),
            )
        ],
    )
    events = GigConsequence().process(actor.world, 5)
    assert any(isinstance(e, GigResolvedEvent) for e in events)


# --------------------------------------------------------------------------------------
# Optional museum synergy: exercise the active consume path with an injected stub.
# --------------------------------------------------------------------------------------


def test_external_reputation_bonus_reads_an_injected_partner_pack():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")

    module = types.ModuleType("bunnyland_museumsim")
    connectors = types.ModuleType("bunnyland_museumsim.connectors")

    def donor_renown(world, character_id):
        return 7

    connectors.donor_renown = donor_renown
    module.connectors = connectors
    sys.modules["bunnyland_museumsim"] = module
    sys.modules["bunnyland_museumsim.connectors"] = connectors
    try:
        assert external_reputation_bonus(actor.world, musician.id) == 7
    finally:
        del sys.modules["bunnyland_museumsim.connectors"]
        del sys.modules["bunnyland_museumsim"]


# --------------------------------------------------------------------------------------
# PerformanceConsequence guard paths (v1 corners the v2 install now runs alongside)
# --------------------------------------------------------------------------------------


def _spawn_perf_noise(world, room_id, *, performer_id, mood="uplifting"):
    return spawn_entity(
        world,
        [
            PerformanceNoiseComponent(
                song="a tune",
                mood=mood,
                performer_id=performer_id,
                performer_name="Lira",
                room_id=room_id,
            )
        ],
    )


def test_performance_consequence_skips_a_vanished_room():
    actor = WorldActor()
    _spawn_perf_noise(actor.world, "ghost_1", performer_id="ghost_2")
    assert PerformanceConsequence().process(actor.world, 5) == []


def test_performance_consequence_ignores_non_character_occupants_and_unknown_mood():
    actor = WorldActor()
    room = _room(actor.world)
    performer = spawn_musician(actor.world, name="Lira", room_id=room.id)
    prop = spawn_entity(actor.world, [IdentityComponent(name="chair", kind="item")])
    _place(actor.world, room, prop)  # not a character -> ignored
    listener = spawn_musician(actor.world, name="Fan", room_id=room.id)
    _spawn_perf_noise(actor.world, str(room.id), performer_id=str(performer.id), mood="nonsense")

    PerformanceConsequence().process(actor.world, 5)

    from bunnyland_bardsim.components import TipJarComponent

    # Unknown mood -> no affect shift, but tips still flow from the lone listener.
    assert performer.get_component(TipJarComponent).coins >= 1
    assert listener.id != performer.id


def test_performance_consequence_no_op_when_performer_has_no_tip_jar():
    actor = WorldActor()
    room = _room(actor.world)
    performer = spawn_entity(
        actor.world, [IdentityComponent(name="Lira", kind="character"), CharacterComponent()]
    )
    _place(actor.world, room, performer)  # deliberately no TipJarComponent
    spawn_musician(actor.world, name="Fan", room_id=room.id)
    _spawn_perf_noise(actor.world, str(room.id), performer_id=str(performer.id))

    # Should not raise even though there is nowhere to bank tips.
    assert PerformanceConsequence().process(actor.world, 5) == []


# --------------------------------------------------------------------------------------
# fragments.py corners
# --------------------------------------------------------------------------------------


def test_bardsim_fragments_first_person_playing_line_and_other_room_skip():
    actor = WorldActor()
    stage = _room(actor.world, "Stage")
    other = _room(actor.world, "Back room")
    musician = spawn_musician(actor.world, name="Lira", room_id=stage.id)
    lute = spawn_lute(actor.world)
    _hold(musician, lute)
    # A performance by the character themselves in their room.
    _spawn_perf_noise(actor.world, str(stage.id), performer_id=str(musician.id))
    # A performance in a different room is not surfaced.
    _spawn_perf_noise(actor.world, str(other.id), performer_id="ghost_1")

    lines = bardsim_fragments(actor.world, musician)
    assert any('You are playing "a tune" here.' == line for line in lines)
    assert not any("Back room" in line for line in lines)


def test_bardsim_fragments_without_a_room():
    actor = WorldActor()
    loner = spawn_entity(
        actor.world, [IdentityComponent(name="Loner", kind="character"), CharacterComponent()]
    )
    replace_component(loner, RepertoireComponent(songs=("a merry harvest jig",)))
    # No room: the "what is playing here" block is skipped; the repertoire line still shows.
    lines = bardsim_fragments(actor.world, loner)
    assert any("You know how to play" in line for line in lines)


def test_repertoire_fragment_is_hidden_from_bystanders_and_when_empty():
    actor = WorldActor()
    room = _room(actor.world)
    owner = spawn_musician(
        actor.world, name="Lira", room_id=room.id, songs=("a merry harvest jig",)
    )
    bystander = spawn_musician(actor.world, name="Bram", room_id=room.id)

    comp = owner.get_component(RepertoireComponent)
    third = ComponentPromptContext.for_entity(
        actor.world, owner, perspective=PromptPerspective(viewer=bystander)
    )
    assert comp.prompt_fragments(third) == ()  # private to the owner

    empty = RepertoireComponent(songs=())
    first = ComponentPromptContext.for_entity(actor.world, owner)
    assert empty.prompt_fragments(first) == ()  # nothing to list


def test_gig_performer_name_falls_back_when_identity_is_missing():
    """A performer without an IdentityComponent still plays a gig; the name is a fallback."""
    actor = WorldActor()
    room = _room(actor.world)
    faceless = spawn_entity(actor.world, [CharacterComponent()])
    _place(actor.world, room, faceless)
    replace_component(faceless, RepertoireComponent(songs=("a merry harvest jig",)))
    from bunnyland_bardsim.venues import OpenVenueHandler, PerformGigHandler

    lute = spawn_lute(actor.world)
    _hold(faceless, lute)
    ctx = HandlerContext(world=actor.world, epoch=0)
    OpenVenueHandler().execute(ctx, _cmd(faceless.id, "open-venue", {"name": "The Rest"}))
    result = PerformGigHandler().execute(
        ctx,
        _cmd(faceless.id, "perform-gig", {"item_id": str(lute.id), "song": "a merry harvest jig"}),
    )
    assert result.ok
    gig = next(iter(actor.world.query().with_all([GigComponent]).execute_entities()))
    assert gig.get_component(GigComponent).performer_name == "someone"


# --------------------------------------------------------------------------------------
# spatial.py corners
# --------------------------------------------------------------------------------------


def test_holder_of_guards():
    actor = WorldActor()
    room = _room(actor.world)
    loose = spawn_lute(actor.world, room_id=room.id)  # in a room, not held
    uncontained = spawn_lute(actor.world)  # no container at all

    assert holder_of(actor.world, _ghost()) is None  # missing entity
    assert holder_of(actor.world, uncontained.id) is None  # no parent
    assert holder_of(actor.world, loose.id) is None  # parent is a room


def test_room_of_guards_and_depth_limit():
    actor = WorldActor()
    assert room_of(actor.world, _ghost()) is None  # missing entity
    uncontained = spawn_lute(actor.world)
    assert room_of(actor.world, uncontained.id) is None  # no parent

    # A containment chain deeper than the guard, with no room at the top, returns None.
    chain = [spawn_entity(actor.world, [IdentityComponent(name=f"box{i}", kind="item")])
             for i in range(10)]
    for outer, inner in zip(chain, chain[1:], strict=False):
        outer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), inner.id)
    assert room_of(actor.world, chain[-1].id) is None


def test_are_bandmates_false_for_a_missing_actor():
    from bunnyland_bardsim.ensembles import are_bandmates

    actor = WorldActor()
    real = spawn_musician(actor.world, name="Lira")
    assert not are_bandmates(actor.world, _ghost(), real.id)


def test_perform_gig_rejects_a_performer_with_no_repertoire_at_all():
    from bunnyland_bardsim.venues import OpenVenueHandler, PerformGigHandler

    actor = WorldActor()
    room = _room(actor.world)
    bare = spawn_entity(
        actor.world, [IdentityComponent(name="Bare", kind="character"), CharacterComponent()]
    )  # never learned a song -> no RepertoireComponent
    _place(actor.world, room, bare)
    lute = spawn_lute(actor.world)
    _hold(bare, lute)
    ctx = HandlerContext(world=actor.world, epoch=0)
    OpenVenueHandler().execute(ctx, _cmd(bare.id, "open-venue", {"name": "The Rest"}))

    result = PerformGigHandler().execute(
        ctx, _cmd(bare.id, "perform-gig", {"item_id": str(lute.id), "song": "any tune"})
    )
    assert result.reason == "you do not know that song"


def test_compositions_of_skips_edges_to_non_composition_entities():
    from bunnyland_bardsim.composing import Composed, compositions_of

    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")
    prop = spawn_entity(actor.world, [IdentityComponent(name="prop", kind="item")])
    musician.add_relationship(Composed(), prop.id)  # not a CompositionComponent
    assert compositions_of(actor.world, musician) == []


def test_noise_and_gig_share_the_room_key():
    """A gig seeds a core NoiseComponent so the hearing pipeline carries it (regression)."""
    actor = WorldActor()
    room = _room(actor.world)
    performer = spawn_musician(actor.world, name="Lira", room_id=room.id)
    spawn_entity(
        actor.world,
        [
            NoiseComponent(
                loudness=3.0,
                text="a tune",
                source_entity_id=str(performer.id),
                room_id=str(room.id),
                created_at_epoch=0,
                expires_at_epoch=60,
            )
        ],
    )
    noises = list(actor.world.query().with_all([NoiseComponent]).execute_entities())
    assert noises and noises[0].get_component(NoiseComponent).room_id == str(room.id)
