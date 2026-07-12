"""Composing: write an original song, own its authorship, and grow a repertoire.

Composing spawns a small composition entity and ties the author to it with a typed
:class:`Composed` edge (authorship is a repeatable relationship, so it is an edge, never a
list on a component). The new title also drops into the composer's core
:class:`RepertoireComponent` so they can immediately perform it, and the creative act earns a
little :data:`COMPOSE_RENOWN` on the shared reputation surface.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import spawn_entity
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.components import IdentityComponent
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_entity,
)
from pydantic.dataclasses import dataclass
from relics import Component, Edge, Entity, World

from .components import RepertoireComponent
from .reputation import grant_renown
from .songs import song_mood
from .spatial import room_of

#: Renown a musician earns for writing an original song.
COMPOSE_RENOWN = 3


@dataclass(frozen=True)
class CompositionComponent(Component):
    """An original song, spawned as its own entity and owned via a :class:`Composed` edge."""

    title: str
    mood: str
    composer_id: str
    composer_name: str
    created_at_epoch: int = 0


@dataclass(frozen=True)
class Composed(Edge):
    """A directed author -> composition tie."""

    created_at_epoch: int = 0


class SongComposedEvent(DomainEvent):
    """A musician wrote an original song."""

    title: str
    mood: str


def compositions_of(world: World, character: Entity) -> list[tuple[Composed, Entity]]:
    """Every ``(edge, composition_entity)`` a character has authored."""
    works: list[tuple[Composed, Entity]] = []
    for edge, comp_id in character.get_relationships(Composed):
        if world.has_entity(comp_id):
            composition = world.get_entity(comp_id)
            if composition.has_component(CompositionComponent):
                works.append((edge, composition))
    return works


class ComposeSongHandler:
    """Write an original song: own it, learn it, and earn a little renown."""

    command_type = "compose-song"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        title = str(command.payload.get("title", "")).strip()
        if not title:
            return rejected("you need to name the composition")
        repertoire = (
            character.get_component(RepertoireComponent)
            if character.has_component(RepertoireComponent)
            else RepertoireComponent()
        )
        if repertoire.knows(title):
            return rejected("you already know that song")
        mood = song_mood(title)
        composer_name = (
            character.get_component(IdentityComponent).name
            if character.has_component(IdentityComponent)
            else "someone"
        )
        composition = spawn_entity(
            ctx.world,
            [
                IdentityComponent(name=title, kind="composition", tags=("bardsim",)),
                CompositionComponent(
                    title=title,
                    mood=mood,
                    composer_id=str(character_id),
                    composer_name=composer_name,
                    created_at_epoch=ctx.epoch,
                ),
            ],
        )
        character.add_relationship(Composed(created_at_epoch=ctx.epoch), composition.id)
        replace_component(character, replace(repertoire, songs=(*repertoire.songs, title)))
        grant_renown(ctx.world, character_id, COMPOSE_RENOWN)
        return ok(
            SongComposedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=_room_id(ctx, character_id),
                    target_ids=(str(composition.id),),
                    title=title,
                    mood=mood,
                )
            )
        )


def _room_id(ctx: HandlerContext, entity_id) -> str | None:
    room = room_of(ctx.world, entity_id)
    return str(room.id) if room is not None else None


def composition_fragments(world: World, character: Entity) -> list[str]:
    """Foundation-prompt line listing a character's own compositions (first person)."""
    works = compositions_of(world, character)
    if not works:
        return []
    titles = sorted(comp.get_component(CompositionComponent).title for _edge, comp in works)
    listing = ", ".join(titles)
    return [f"You have composed: {listing}."]


COMPOSE_SONG_DEF = ActionDefinition(
    command_type="compose-song",
    title="Compose a song",
    description="Write an original song, learn it, and add it to your body of work.",
    lane=Lane.FOCUS,
    cost=effort_cost(focus=ActionEffort.EXTENDED),
    arguments={
        "title": ActionArgument(
            title="Title",
            description="The title of the song to compose.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = [
    "COMPOSE_RENOWN",
    "COMPOSE_SONG_DEF",
    "Composed",
    "ComposeSongHandler",
    "CompositionComponent",
    "SongComposedEvent",
    "composition_fragments",
    "compositions_of",
]
