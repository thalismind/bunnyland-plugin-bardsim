"""Venues & gigs: the headline v2 mechanic.

A room becomes a :class:`VenueComponent` stage; a ``perform-gig`` there is a full performance
that *also* builds reputation. The gig reuses the v1 performance pipeline wholesale — it
spawns the same ``NoiseComponent`` + :class:`PerformanceNoiseComponent`, so the core hearing
system carries the tune and the v1 :class:`~bunnyland_bardsim.performance.PerformanceConsequence`
still shifts audience mood and pays busking tips. The new :class:`GigConsequence` layers renown
on top:

- it grants the performer (and every present bandmate) renown scaled by the venue's prestige,
  the crowd size, the ensemble, and any optional partner-pack reputation bonus;
- it **publishes a ``ContestEntry``** so a festival pack can host the gig as a competition;
- and when a performer crosses :data:`~bunnyland_bardsim.reputation.FAME_THRESHOLD`, it
  **registers a storyteller incident** — a famous act draws a crowd — using the core
  storyteller's own incident surface.
"""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    NoiseComponent,
    contents,
    spawn_entity,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.components import IdentityComponent
from bunnyland.core.ecs import parse_entity_id
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_entity,
)
from bunnyland.core.mutations import AddEntity, MutationPlan, SetComponent
from bunnyland.foundation.storyteller.mechanics import IncidentComponent, IncidentStartedEvent
from pydantic.dataclasses import dataclass
from relics import Component, World

from .commands import PERFORMANCE_LOUDNESS, PERFORMANCE_TTL
from .components import (
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
)
from .connectors import ContestEntryComponent, external_reputation_bonus
from .ensembles import present_bandmates
from .reputation import grant_renown, is_famous, reputation_of
from .songs import song_mood
from .spatial import holder_of, room_of

#: Renown a gig earns per point of venue prestige, before crowd and ensemble bonuses.
GIG_BASE_RENOWN = 5

#: Extra renown a gig earns for each bandmate who plays alongside the performer.
BANDMATE_BONUS = 2

#: The highest prestige a venue may be opened at.
MAX_PRESTIGE = 5

#: The kind of storyteller incident a famous act registers.
FAMOUS_ACT_INCIDENT = "famous_act"


@dataclass(frozen=True)
class VenueComponent(Component):
    """Marks a room as a performance venue with a name and a prestige tier (1-5)."""

    name: str = "the stage"
    prestige: int = 1

    def prompt_fragments(self, ctx) -> tuple[str, ...]:
        return (f"This is {self.name}, a performance venue (prestige {self.prestige}).",)


@dataclass(frozen=True)
class GigComponent(Component):
    """Marks a gig's throwaway noise entity so :class:`GigConsequence` can reward it."""

    performer_id: str
    performer_name: str
    song: str
    mood: str
    venue_id: str
    venue_name: str
    prestige: int
    room_id: str


class VenueOpenedEvent(DomainEvent):
    """A room was opened as a performance venue."""

    venue_name: str
    prestige: int


class GigPerformedEvent(DomainEvent):
    """A character played a gig at a venue."""

    venue_id: str
    venue_name: str
    song: str
    mood: str


class GigResolvedEvent(DomainEvent):
    """A gig was scored: renown granted and a contest entry published."""

    performer_id: str
    venue_id: str
    score: int
    audience_size: int


class OpenVenueHandler:
    """Turn the acting character's current room into a named performance venue."""

    command_type = "open-venue"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("there is no room to open as a venue")
        name = str(command.payload.get("name", "")).strip()
        if not name:
            return rejected("you need to name the venue")
        prestige_raw = command.payload.get("prestige", 1)
        try:
            prestige = int(prestige_raw)
        except (TypeError, ValueError):
            return rejected("prestige must be a number")
        prestige = max(1, min(MAX_PRESTIGE, prestige))
        if room.has_component(VenueComponent):
            return rejected("this room is already a venue")
        return planned(
            MutationPlan((SetComponent(room.id, VenueComponent(name=name, prestige=prestige)),)),
            VenueOpenedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(room.id),),
                    venue_name=name,
                    prestige=prestige,
                )
            ),
        )


class PerformGigHandler:
    """Play a known song on a held instrument at a venue, seeding a scored gig."""

    command_type = "perform-gig"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        item_id, item, rejection = require_entity(
            ctx,
            command.payload.get("item_id"),
            invalid_reason="invalid item id",
            missing_reason="item does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, item_id)
        if holder is None or holder.id != character_id:
            return rejected("you are not holding that instrument")
        if not item.has_component(InstrumentComponent):
            return rejected("that is not an instrument")
        song = str(command.payload.get("song", "")).strip()
        if not song:
            return rejected("you need to name a song to perform")
        repertoire = (
            character.get_component(RepertoireComponent)
            if character.has_component(RepertoireComponent)
            else None
        )
        if repertoire is None or not repertoire.knows(song):
            return rejected("you do not know that song")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("there is no room to perform in")
        if not room.has_component(VenueComponent):
            return rejected("you can only play a gig at a venue")

        venue = room.get_component(VenueComponent)
        mood = song_mood(song)
        performer_name = _name_of(character)
        operations = [
            AddEntity(
                (
                    NoiseComponent(
                        loudness=PERFORMANCE_LOUDNESS,
                        text=song,
                        source_entity_id=str(item_id),
                        room_id=str(room.id),
                        created_at_epoch=ctx.epoch,
                        expires_at_epoch=ctx.epoch + PERFORMANCE_TTL,
                    ),
                    PerformanceNoiseComponent(
                        song=song,
                        mood=mood,
                        performer_id=str(character_id),
                        performer_name=performer_name,
                        room_id=str(room.id),
                    ),
                    GigComponent(
                        performer_id=str(character_id),
                        performer_name=performer_name,
                        song=song,
                        mood=mood,
                        venue_id=str(room.id),
                        venue_name=venue.name,
                        prestige=venue.prestige,
                        room_id=str(room.id),
                    ),
                )
            )
        ]
        if not character.has_component(TipJarComponent):
            operations.append(SetComponent(character.id, TipJarComponent()))
        return planned(
            MutationPlan(tuple(operations)),
            GigPerformedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(item_id),),
                    venue_id=str(room.id),
                    venue_name=venue.name,
                    song=song,
                    mood=mood,
                )
            ),
        )


class GigConsequence:
    """Score each gig once: grant renown, publish a contest entry, register fame incidents."""

    def __init__(self) -> None:
        # Gig noise entities already scored, so a gig that lingers for many ticks is rewarded
        # exactly once (mirrors the v1 performance bookkeeping).
        self._resolved: set[str] = set()
        # Performers already feted with a crowd-drawing incident, so fame fires only once.
        self._feted: set[str] = set()

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        seen: set[str] = set()
        for gig_entity in list(world.query().with_all([GigComponent]).execute_entities()):
            key = str(gig_entity.id)
            seen.add(key)
            if key in self._resolved:
                continue
            self._resolved.add(key)
            events.extend(self._score(world, epoch, gig_entity.get_component(GigComponent)))
        self._resolved &= seen
        return events

    def _score(self, world: World, epoch: int, gig: GigComponent) -> list[DomainEvent]:
        room_id = parse_entity_id(gig.room_id)
        performer_id = parse_entity_id(gig.performer_id)
        if room_id is None or performer_id is None or not world.has_entity(room_id):
            return []
        room = world.get_entity(room_id)
        audience = _audience(world, room, performer_id)
        bandmates: list = []
        if world.has_entity(performer_id):
            performer = world.get_entity(performer_id)
            bandmates = present_bandmates(world, performer, room_id)
        score = (
            gig.prestige * GIG_BASE_RENOWN
            + len(audience)
            + len(bandmates) * BANDMATE_BONUS
            + external_reputation_bonus(world, performer_id)
        )
        grant_renown(world, performer_id, score)
        share = max(1, score // 2)
        for bandmate in bandmates:
            grant_renown(world, bandmate.id, share)
        _publish_contest_entry(world, epoch, gig, score)
        events: list[DomainEvent] = [
            GigResolvedEvent(
                **event_base(
                    epoch,
                    visibility=EventVisibility.ROOM,
                    actor_id=gig.performer_id,
                    room_id=gig.room_id,
                    target_ids=(gig.venue_id,),
                    performer_id=gig.performer_id,
                    venue_id=gig.venue_id,
                    score=score,
                    audience_size=len(audience),
                )
            )
        ]
        incident = self._maybe_fete(world, epoch, gig, performer_id, room)
        if incident is not None:
            events.append(incident)
        return events

    def _maybe_fete(self, world, epoch, gig, performer_id, room) -> DomainEvent | None:
        if gig.performer_id in self._feted or not is_famous(reputation_of(world, performer_id)):
            return None
        self._feted.add(gig.performer_id)
        incident = spawn_entity(
            world,
            [
                IdentityComponent(name="a famous act draws a crowd", kind="incident"),
                IncidentComponent(
                    kind=FAMOUS_ACT_INCIDENT,
                    budget_spent=0.0,
                    started_at_epoch=epoch,
                    room_id=gig.room_id,
                ),
            ],
        )
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), incident.id)
        return IncidentStartedEvent(
            **event_base(
                epoch,
                visibility=EventVisibility.ROOM,
                actor_id=gig.performer_id,
                room_id=gig.room_id,
                target_ids=(str(incident.id),),
                incident_id=str(incident.id),
                kind=FAMOUS_ACT_INCIDENT,
                room_id_started=gig.room_id,
            )
        )


def _audience(world: World, room, performer_id) -> list:
    audience = []
    for occupant_id in contents(room):
        if not world.has_entity(occupant_id) or occupant_id == performer_id:
            continue
        occupant = world.get_entity(occupant_id)
        if occupant.has_component(CharacterComponent):
            audience.append(occupant)
    return audience


def _publish_contest_entry(world: World, epoch: int, gig: GigComponent, score: int) -> None:
    spawn_entity(
        world,
        [
            IdentityComponent(name=f'gig entry: "{gig.song}"', kind="contest-entry"),
            ContestEntryComponent(
                entry_kind="gig",
                performer_id=gig.performer_id,
                performer_name=gig.performer_name,
                song=gig.song,
                mood=gig.mood,
                venue_id=gig.venue_id,
                venue_name=gig.venue_name,
                score=score,
                created_at_epoch=epoch,
            ),
        ],
    )


def _name_of(entity) -> str:
    if entity.has_component(IdentityComponent):
        return entity.get_component(IdentityComponent).name
    return "someone"


def venue_fragments(world: World, character) -> list[str]:
    """Foundation-prompt line naming the venue a character is standing in, if any."""
    room = room_of(world, character.id)
    if room is None or not room.has_component(VenueComponent):
        return []
    return list(room.get_component(VenueComponent).prompt_fragments(None))


OPEN_VENUE_DEF = ActionDefinition(
    command_type="open-venue",
    title="Open a venue",
    description="Turn the room you are in into a named performance venue.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.MAJOR),
    arguments={
        "name": ActionArgument(
            title="Venue name",
            description="The name of the venue.",
            kind="string",
            required=True,
        ),
        "prestige": ActionArgument(
            title="Prestige",
            description="How prestigious the venue is (1-5).",
            kind="number",
            required=False,
        ),
    },
)

PERFORM_GIG_DEF = ActionDefinition(
    command_type="perform-gig",
    title="Play a gig",
    description="Perform a known song at a venue to build your reputation.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.EXTENDED),
    arguments={
        "item_id": ActionArgument(
            title="Instrument",
            description="The instrument to play.",
            kind="entity",
            required=True,
        ),
        "song": ActionArgument(
            title="Song",
            description="A song from your repertoire to perform.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = [
    "BANDMATE_BONUS",
    "FAMOUS_ACT_INCIDENT",
    "GIG_BASE_RENOWN",
    "MAX_PRESTIGE",
    "OPEN_VENUE_DEF",
    "PERFORM_GIG_DEF",
    "GigComponent",
    "GigConsequence",
    "GigPerformedEvent",
    "GigResolvedEvent",
    "OpenVenueHandler",
    "PerformGigHandler",
    "VenueComponent",
    "VenueOpenedEvent",
    "venue_fragments",
]
