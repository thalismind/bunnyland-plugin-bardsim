"""Behaviour tests for the bardsim v2 bundle: ensembles, venues/gigs, reputation, composing."""

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
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import parse_entity_id
from bunnyland.core.handlers import HandlerContext
from bunnyland.mechanics.persona import GoalComponent
from bunnyland.mechanics.storyteller import IncidentComponent, IncidentStartedEvent

from bunnyland_bardsim.composing import (
    COMPOSE_RENOWN,
    Composed,
    ComposeSongHandler,
    CompositionComponent,
    SongComposedEvent,
    composition_fragments,
    compositions_of,
)
from bunnyland_bardsim.connectors import (
    ContestEntryComponent,
    Reputation,
    contest_entries,
    external_reputation_bonus,
)
from bunnyland_bardsim.ensembles import (
    BandmateOf,
    EnsembleFormedEvent,
    FormEnsembleHandler,
    are_bandmates,
    bandmates_of,
    ensemble_fragments,
    present_bandmates,
)
from bunnyland_bardsim.prefabs import spawn_lute, spawn_musician
from bunnyland_bardsim.reputation import (
    FAME_THRESHOLD,
    RENOWNED_GOAL,
    aspire_to_renown,
    grant_renown,
    is_famous,
    reputation_fragments,
    reputation_of,
    standing,
)
from bunnyland_bardsim.venues import (
    GIG_BASE_RENOWN,
    GigComponent,
    GigConsequence,
    GigPerformedEvent,
    GigResolvedEvent,
    OpenVenueHandler,
    PerformGigHandler,
    VenueComponent,
    VenueOpenedEvent,
    venue_fragments,
)

SONG = "a merry harvest jig"

# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


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


def _run(handler_cls, actor, character, command_type, payload=None, epoch=0):
    ctx = HandlerContext(world=actor.world, epoch=epoch)
    return handler_cls().execute(ctx, _cmd(character.id, command_type, payload))


def _ghost_id():
    return parse_entity_id("ghost_999")


def _venue_setup(prestige=1):
    """A world, a venue room, and a musician holding a lute who knows SONG."""
    actor = WorldActor()
    room = _room(actor.world)
    musician = spawn_musician(actor.world, name="Lira", room_id=room.id)
    lute = spawn_lute(actor.world)
    _hold(musician, lute)
    _run(
        OpenVenueHandler, actor, musician, "open-venue",
        {"name": "The Rest", "prestige": prestige},
    )
    return actor, room, musician, lute


# --------------------------------------------------------------------------------------
# ensembles (a typed BandmateOf edge)
# --------------------------------------------------------------------------------------


def test_form_ensemble_links_both_musicians():
    actor = WorldActor()
    room = _room(actor.world)
    lira = spawn_musician(actor.world, name="Lira", room_id=room.id)
    bram = spawn_musician(actor.world, name="Bram", room_id=room.id)

    result = _run(
        FormEnsembleHandler, actor, lira, "form-ensemble",
        {"member_id": str(bram.id), "band": "The Wanderers"},
    )

    assert result.ok
    assert isinstance(result.events[0], EnsembleFormedEvent)
    assert result.events[0].band == "The Wanderers"
    # A symmetric typed edge, one index each way -- not a list on a component.
    assert are_bandmates(actor.world, lira.id, bram.id)
    assert are_bandmates(actor.world, bram.id, lira.id)
    assert [m for _e, m in bandmates_of(actor.world, lira)] == [bram.id]


def test_form_ensemble_rejections():
    actor = WorldActor()
    room = _room(actor.world)
    lira = spawn_musician(actor.world, name="Lira", room_id=room.id)
    bram = spawn_musician(actor.world, name="Bram", room_id=room.id)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    _place(actor.world, room, rock)

    invalid = _run(FormEnsembleHandler, actor, lira, "form-ensemble", {"member_id": "nope"})
    assert invalid.reason == "invalid member id"

    missing = _run(FormEnsembleHandler, actor, lira, "form-ensemble", {"member_id": "ghost_1"})
    assert missing.reason == "member does not exist"

    myself = _run(FormEnsembleHandler, actor, lira, "form-ensemble", {"member_id": str(lira.id)})
    assert myself.reason == "you cannot form an ensemble with yourself"

    not_musician = _run(
        FormEnsembleHandler, actor, lira, "form-ensemble", {"member_id": str(rock.id)}
    )
    assert not_musician.reason == "that is not a musician"

    no_name = _run(
        FormEnsembleHandler, actor, lira, "form-ensemble", {"member_id": str(bram.id)}
    )
    assert no_name.reason == "you need to name the ensemble"

    _run(
        FormEnsembleHandler, actor, lira, "form-ensemble",
        {"member_id": str(bram.id), "band": "Duo"},
    )
    again = _run(
        FormEnsembleHandler, actor, lira, "form-ensemble",
        {"member_id": str(bram.id), "band": "Duo"},
    )
    assert again.reason == "you already share an ensemble"


def test_form_ensemble_rejects_invalid_actor():
    actor = WorldActor()
    stray = spawn_entity(actor.world, [IdentityComponent(name="?", kind="character")])
    ctx = HandlerContext(world=actor.world, epoch=0)
    result = FormEnsembleHandler().execute(
        ctx, _cmd("bad", "form-ensemble", {"member_id": str(stray.id)})
    )
    assert result.reason == "invalid character id"


def test_present_bandmates_only_counts_those_in_the_room():
    actor = WorldActor()
    stage = _room(actor.world, "Stage")
    elsewhere = _room(actor.world, "Back alley")
    lira = spawn_musician(actor.world, name="Lira", room_id=stage.id)
    bram = spawn_musician(actor.world, name="Bram", room_id=stage.id)
    zed = spawn_musician(actor.world, name="Zed", room_id=elsewhere.id)
    lira.add_relationship(BandmateOf(band="Trio"), bram.id)
    lira.add_relationship(BandmateOf(band="Trio"), zed.id)  # bandmate, but a room away

    present = present_bandmates(actor.world, lira, stage.id)
    assert [m.id for m in present] == [bram.id]


def test_ensemble_fragments_names_bandmates_first_person():
    actor = WorldActor()
    room = _room(actor.world)
    lira = spawn_musician(actor.world, name="Lira", room_id=room.id)
    bram = spawn_musician(actor.world, name="Bram", room_id=room.id)
    assert ensemble_fragments(actor.world, lira) == []  # no ties yet

    lira.add_relationship(BandmateOf(band="The Wanderers"), bram.id)
    lines = ensemble_fragments(actor.world, lira)
    assert lines == ['Your ensemble "The Wanderers" also features Bram.']


def test_ensemble_fragments_skip_nameless_members():
    actor = WorldActor()
    room = _room(actor.world)
    lira = spawn_musician(actor.world, name="Lira", room_id=room.id)
    nameless = spawn_entity(actor.world, [CharacterComponent()])  # no IdentityComponent
    lira.add_relationship(BandmateOf(band="Ghosts"), nameless.id)
    assert ensemble_fragments(actor.world, lira) == []


# --------------------------------------------------------------------------------------
# venues & gigs (the headline mechanic)
# --------------------------------------------------------------------------------------


def test_open_venue_marks_the_room():
    actor = WorldActor()
    room = _room(actor.world)
    host = spawn_musician(actor.world, name="Host", room_id=room.id)

    result = _run(OpenVenueHandler, actor, host, "open-venue", {"name": "The Rest", "prestige": 3})

    assert result.ok and isinstance(result.events[0], VenueOpenedEvent)
    assert room.has_component(VenueComponent)
    assert room.get_component(VenueComponent).prestige == 3


def test_open_venue_clamps_prestige_and_rejects():
    actor = WorldActor()
    room = _room(actor.world)
    host = spawn_musician(actor.world, name="Host", room_id=room.id)

    # Above MAX_PRESTIGE clamps to 5.
    _run(OpenVenueHandler, actor, host, "open-venue", {"name": "Grand", "prestige": 99})
    assert room.get_component(VenueComponent).prestige == 5

    already = _run(OpenVenueHandler, actor, host, "open-venue", {"name": "Again", "prestige": 1})
    assert already.reason == "this room is already a venue"


def test_open_venue_rejections():
    actor = WorldActor()
    room = _room(actor.world)
    host = spawn_musician(actor.world, name="Host", room_id=room.id)
    stray = spawn_entity(actor.world, [IdentityComponent(name="Stray", kind="character")])

    no_name = _run(OpenVenueHandler, actor, host, "open-venue", {"name": "  "})
    assert no_name.reason == "you need to name the venue"

    bad_prestige = _run(
        OpenVenueHandler, actor, host, "open-venue", {"name": "Odd", "prestige": "loud"}
    )
    assert bad_prestige.reason == "prestige must be a number"

    no_room = _run(OpenVenueHandler, actor, stray, "open-venue", {"name": "Nowhere"})
    assert no_room.reason == "there is no room to open as a venue"

    ctx = HandlerContext(world=actor.world, epoch=0)
    bad_actor = OpenVenueHandler().execute(ctx, _cmd("bad", "open-venue", {"name": "X"}))
    assert bad_actor.reason == "invalid character id"


def test_perform_gig_seeds_a_scored_gig():
    actor, room, musician, lute = _venue_setup(prestige=2)

    result = _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )

    assert result.ok and isinstance(result.events[0], GigPerformedEvent)
    gigs = list(actor.world.query().with_all([GigComponent]).execute_entities())
    assert len(gigs) == 1
    assert gigs[0].get_component(GigComponent).prestige == 2


def test_perform_gig_rejections():
    actor, room, musician, lute = _venue_setup()
    loose = spawn_lute(actor.world, room_id=room.id)  # not held
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    _hold(musician, rock)

    bad_item = _run(PerformGigHandler, actor, musician, "perform-gig", {"item_id": "nope"})
    assert bad_item.reason == "invalid item id"

    missing_item = _run(
        PerformGigHandler, actor, musician, "perform-gig", {"item_id": "ghost_1"}
    )
    assert missing_item.reason == "item does not exist"

    not_held = _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(loose.id), "song": SONG},
    )
    assert not_held.reason == "you are not holding that instrument"

    not_instrument = _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(rock.id), "song": SONG},
    )
    assert not_instrument.reason == "that is not an instrument"

    no_song = _run(
        PerformGigHandler, actor, musician, "perform-gig", {"item_id": str(lute.id)}
    )
    assert no_song.reason == "you need to name a song to perform"

    unknown = _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": "a song i never learned"},
    )
    assert unknown.reason == "you do not know that song"


def test_perform_gig_rejects_off_venue_and_roomless():
    actor = WorldActor()
    plain = _room(actor.world)
    musician = spawn_musician(actor.world, name="Lira", room_id=plain.id)
    lute = spawn_lute(actor.world)
    _hold(musician, lute)

    off_venue = _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )
    assert off_venue.reason == "you can only play a gig at a venue"

    # A held instrument with no room at all: performer is uncontained.
    stray = spawn_entity(
        actor.world, [IdentityComponent(name="Stray", kind="character"), CharacterComponent()]
    )
    from bunnyland.core.ecs import replace_component

    from bunnyland_bardsim.components import RepertoireComponent

    replace_component(stray, RepertoireComponent(songs=(SONG,)))
    stray_lute = spawn_lute(actor.world)
    _hold(stray, stray_lute)
    no_room = _run(
        PerformGigHandler, actor, stray, "perform-gig",
        {"item_id": str(stray_lute.id), "song": SONG},
    )
    assert no_room.reason == "there is no room to perform in"


def test_gig_consequence_scores_once_and_publishes_a_contest_entry():
    actor, room, musician, lute = _venue_setup(prestige=3)
    audience = spawn_musician(actor.world, name="Fan", room_id=room.id)  # a listener
    _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )

    events = GigConsequence().process(actor.world, 10)

    resolved = [e for e in events if isinstance(e, GigResolvedEvent)]
    assert len(resolved) == 1
    # prestige 3 * base 5 + 1 audience member = 16.
    assert resolved[0].score == 3 * GIG_BASE_RENOWN + 1
    assert resolved[0].audience_size == 1
    assert reputation_of(actor.world, musician.id).renown == resolved[0].score
    entries = contest_entries(actor.world)
    assert len(entries) == 1 and entries[0].song == SONG and entries[0].entry_kind == "gig"
    assert audience.id != musician.id


def test_gig_consequence_is_idempotent():
    actor, room, musician, lute = _venue_setup(prestige=2)
    _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )
    conseq = GigConsequence()
    first = conseq.process(actor.world, 5)
    second = conseq.process(actor.world, 6)

    assert any(isinstance(e, GigResolvedEvent) for e in first)
    assert second == []  # scored exactly once
    assert len(contest_entries(actor.world)) == 1
    assert reputation_of(actor.world, musician.id).renown == 2 * GIG_BASE_RENOWN


def test_gig_shares_renown_with_present_bandmates():
    actor, room, musician, lute = _venue_setup(prestige=4)
    bram = spawn_musician(actor.world, name="Bram", room_id=room.id)
    _run(
        FormEnsembleHandler, actor, musician, "form-ensemble",
        {"member_id": str(bram.id), "band": "The Wanderers"},
    )
    _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )

    GigConsequence().process(actor.world, 10)

    # bram is both audience (a character in the room) and a bandmate.
    performer_renown = reputation_of(actor.world, musician.id).renown
    bram_renown = reputation_of(actor.world, bram.id).renown
    assert performer_renown > 0
    assert bram_renown == max(1, performer_renown // 2)


def test_a_famous_act_registers_a_storyteller_incident_once():
    actor, room, musician, lute = _venue_setup(prestige=5)
    grant_renown(actor.world, musician.id, FAME_THRESHOLD)  # already renowned
    conseq = GigConsequence()

    # First gig: crosses fame -> a storyteller incident is registered.
    _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )
    first = conseq.process(actor.world, 10)
    incidents = [e for e in first if isinstance(e, IncidentStartedEvent)]
    assert len(incidents) == 1
    assert incidents[0].kind == "famous_act"
    stamped = list(actor.world.query().with_all([IncidentComponent]).execute_entities())
    assert len(stamped) == 1

    # A second gig by the same star does not double-fete.
    _run(
        PerformGigHandler, actor, musician, "perform-gig",
        {"item_id": str(lute.id), "song": SONG},
    )
    second = conseq.process(actor.world, 20)
    assert not [e for e in second if isinstance(e, IncidentStartedEvent)]
    assert len(list(actor.world.query().with_all([IncidentComponent]).execute_entities())) == 1


def test_venue_fragments():
    actor, room, musician, lute = _venue_setup(prestige=2)
    lines = venue_fragments(actor.world, musician)
    assert lines == ["This is The Rest, a performance venue (prestige 2)."]

    plain_actor = WorldActor()
    plain_room = _room(plain_actor.world)
    plain = spawn_musician(plain_actor.world, name="Nobody", room_id=plain_room.id)
    assert venue_fragments(plain_actor.world, plain) == []


# --------------------------------------------------------------------------------------
# composing (a typed Composed edge)
# --------------------------------------------------------------------------------------


def test_compose_song_owns_learns_and_earns_renown():
    actor = WorldActor()
    room = _room(actor.world)
    musician = spawn_musician(actor.world, name="Lira", room_id=room.id, songs=())

    result = _run(
        ComposeSongHandler, actor, musician, "compose-song", {"title": "Ballad of the Bright Dawn"}
    )

    assert result.ok and isinstance(result.events[0], SongComposedEvent)
    assert result.events[0].title == "Ballad of the Bright Dawn"
    assert result.events[0].mood == "uplifting"
    # Authorship is a typed edge to a spawned composition entity.
    works = compositions_of(actor.world, musician)
    assert len(works) == 1
    assert isinstance(works[0][0], Composed)
    assert works[0][1].has_component(CompositionComponent)
    # The new title lands in the core repertoire so it can be performed at once.
    from bunnyland_bardsim.components import RepertoireComponent

    assert musician.get_component(RepertoireComponent).knows("Ballad of the Bright Dawn")
    assert reputation_of(actor.world, musician.id).renown == COMPOSE_RENOWN


def test_compose_song_rejections():
    actor = WorldActor()
    room = _room(actor.world)
    musician = spawn_musician(actor.world, name="Lira", room_id=room.id, songs=(SONG,))

    no_title = _run(ComposeSongHandler, actor, musician, "compose-song", {"title": "   "})
    assert no_title.reason == "you need to name the composition"

    known = _run(ComposeSongHandler, actor, musician, "compose-song", {"title": SONG})
    assert known.reason == "you already know that song"

    ctx = HandlerContext(world=actor.world, epoch=0)
    bad_actor = ComposeSongHandler().execute(ctx, _cmd("bad", "compose-song", {"title": "X"}))
    assert bad_actor.reason == "invalid character id"


def test_compose_song_works_for_a_character_without_a_prior_repertoire():
    actor = WorldActor()
    room = _room(actor.world)
    bare = spawn_entity(
        actor.world, [IdentityComponent(name="Newcomer", kind="character"), CharacterComponent()]
    )
    _place(actor.world, room, bare)

    result = _run(ComposeSongHandler, actor, bare, "compose-song", {"title": "A Quiet Tune"})

    assert result.ok
    from bunnyland_bardsim.components import RepertoireComponent

    assert bare.get_component(RepertoireComponent).knows("A Quiet Tune")


def test_composition_fragments_lists_own_work():
    actor = WorldActor()
    room = _room(actor.world)
    musician = spawn_musician(actor.world, name="Lira", room_id=room.id, songs=())
    assert composition_fragments(actor.world, musician) == []

    _run(ComposeSongHandler, actor, musician, "compose-song", {"title": "Song of the Sea"})
    _run(ComposeSongHandler, actor, musician, "compose-song", {"title": "A Winter Dirge"})
    lines = composition_fragments(actor.world, musician)
    assert lines == ["You have composed: A Winter Dirge, Song of the Sea."]


# --------------------------------------------------------------------------------------
# reputation & goals (persona/goals reuse)
# --------------------------------------------------------------------------------------


def test_standing_tiers():
    assert standing(0) == "unknown"
    assert standing(5) == "known"
    assert standing(20) == "notable"
    assert standing(50) == "celebrated"
    assert standing(100) == "renowned"
    assert standing(-3) == "unknown"


def test_grant_renown_creates_clamps_and_guards_missing():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")

    assert reputation_of(actor.world, musician.id) is None  # none yet
    grant_renown(actor.world, musician.id, 30)
    assert reputation_of(actor.world, musician.id).renown == 30
    grant_renown(actor.world, musician.id, -100)  # cannot go below zero
    assert reputation_of(actor.world, musician.id).renown == 0

    assert grant_renown(actor.world, _ghost_id(), 5) is None
    assert reputation_of(actor.world, _ghost_id()) is None


def test_reputation_of_without_component():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")
    assert reputation_of(actor.world, musician.id) is None


def test_is_famous():
    assert not is_famous(None)
    assert not is_famous(Reputation(renown=FAME_THRESHOLD - 1))
    assert is_famous(Reputation(renown=FAME_THRESHOLD))


def test_aspire_to_renown_routes_through_core_goals_idempotently():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")

    aspire_to_renown(musician)
    assert RENOWNED_GOAL in musician.get_component(GoalComponent).active_goals
    aspire_to_renown(musician)  # idempotent -- not doubled
    assert musician.get_component(GoalComponent).active_goals.count(RENOWNED_GOAL) == 1


def test_aspire_to_renown_preserves_existing_goals():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")
    from bunnyland.core.ecs import replace_component

    replace_component(musician, GoalComponent(active_goals=("find a home",)))
    aspire_to_renown(musician)
    goals = musician.get_component(GoalComponent).active_goals
    assert "find a home" in goals and RENOWNED_GOAL in goals


def test_reputation_fragments_first_person_standing_and_third_person_star():
    actor = WorldActor()
    room = _room(actor.world)
    me = spawn_musician(actor.world, name="Me", room_id=room.id)
    star = spawn_musician(actor.world, name="Vega", room_id=room.id)
    nobody = spawn_musician(actor.world, name="Quiet", room_id=room.id)

    # No renown -> no self line.
    assert reputation_fragments(actor.world, me) == []

    grant_renown(actor.world, me.id, 25)  # notable
    grant_renown(actor.world, star.id, FAME_THRESHOLD)  # renowned peer in the room
    grant_renown(actor.world, nobody.id, 10)  # present but not famous
    lines = reputation_fragments(actor.world, me)
    assert "Your standing as a performer is notable (renown 25)." in lines
    assert "Vega is a renowned performer." in lines
    assert not any("Quiet" in line for line in lines)


def test_reputation_fragments_without_a_room():
    actor = WorldActor()
    loner = spawn_musician(actor.world, name="Loner")  # uncontained
    grant_renown(actor.world, loner.id, 60)
    assert reputation_fragments(actor.world, loner) == [
        "Your standing as a performer is celebrated (renown 60)."
    ]


# --------------------------------------------------------------------------------------
# connectors (published surfaces + optional consumption)
# --------------------------------------------------------------------------------------


def test_external_reputation_bonus_is_zero_without_the_museum_pack():
    actor = WorldActor()
    musician = spawn_musician(actor.world, name="Lira")
    # No museum pack loaded: the conditional import fails and the synergy stays off.
    assert external_reputation_bonus(actor.world, musician.id) == 0


def test_connector_defaults():
    assert Reputation().renown == 0
    entry = ContestEntryComponent()
    assert entry.entry_kind == "gig" and entry.score == 0
