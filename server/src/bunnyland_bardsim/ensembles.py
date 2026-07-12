"""Ensembles: bandmates modelled as a typed :class:`BandmateOf` edge.

A band is *not* a list on a component. Each membership is a directed :class:`BandmateOf`
edge, so the relationship gets its own Relics index and queries stay efficient. Forming an
ensemble links two musicians symmetrically (an edge each way) under a shared band name; a gig
then rewards every present bandmate, so a group draws more renown than a lone busker.
"""

from __future__ import annotations

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.components import CharacterComponent, IdentityComponent
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_entity,
)
from pydantic.dataclasses import dataclass
from relics import Edge, Entity, EntityId, World

from .spatial import room_of


@dataclass(frozen=True)
class BandmateOf(Edge):
    """A directed band-membership tie between two musicians (shares a band name)."""

    band: str = ""


class EnsembleFormedEvent(DomainEvent):
    """Two musicians joined the same ensemble."""

    member_id: str
    band: str


def bandmates_of(world: World, character: Entity) -> list[tuple[BandmateOf, EntityId]]:
    """Every ``(edge, member_id)`` band tie a character has."""
    return list(character.get_relationships(BandmateOf))


def are_bandmates(world: World, a_id: EntityId, b_id: EntityId) -> bool:
    """Whether ``a`` already shares an ensemble with ``b``."""
    if not world.has_entity(a_id):
        return False
    return world.get_entity(a_id).has_relationship(BandmateOf, b_id)


def present_bandmates(world: World, character: Entity, room_id: EntityId) -> list[Entity]:
    """Bandmates of ``character`` who are in ``room_id`` right now."""
    members: list[Entity] = []
    for _edge, member_id in character.get_relationships(BandmateOf):
        if not world.has_entity(member_id):
            continue
        member = world.get_entity(member_id)
        member_room = room_of(world, member_id)
        if member_room is not None and member_room.id == room_id:
            members.append(member)
    return members


class FormEnsembleHandler:
    """Link the acting musician and another into a shared, named ensemble."""

    command_type = "form-ensemble"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        member_id, member, rejection = require_entity(
            ctx,
            command.payload.get("member_id"),
            invalid_reason="invalid member id",
            missing_reason="member does not exist",
        )
        if rejection is not None:
            return rejection
        if member_id == character_id:
            return rejected("you cannot form an ensemble with yourself")
        if not member.has_component(CharacterComponent):
            return rejected("that is not a musician")
        band = str(command.payload.get("band", "")).strip()
        if not band:
            return rejected("you need to name the ensemble")
        if are_bandmates(ctx.world, character_id, member_id):
            return rejected("you already share an ensemble")
        character.add_relationship(BandmateOf(band=band), member_id)
        member.add_relationship(BandmateOf(band=band), character_id)
        return ok(
            EnsembleFormedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=_room_id(ctx, character_id),
                    target_ids=(str(member_id),),
                    member_id=str(member_id),
                    band=band,
                )
            )
        )


def _room_id(ctx: HandlerContext, entity_id: EntityId) -> str | None:
    room = room_of(ctx.world, entity_id)
    return str(room.id) if room is not None else None


def ensemble_fragments(world: World, character: Entity) -> list[str]:
    """Foundation-prompt line naming a character's bandmates (first person only)."""
    ties = character.get_relationships(BandmateOf)
    if not ties:
        return []
    names: list[str] = []
    for _edge, member_id in ties:
        if not world.has_entity(member_id):
            continue
        member = world.get_entity(member_id)
        if member.has_component(IdentityComponent):
            names.append(member.get_component(IdentityComponent).name)
    if not names:
        return []
    band = ties[0][0].band
    listing = ", ".join(sorted(names))
    return [f'Your ensemble "{band}" also features {listing}.']


FORM_ENSEMBLE_DEF = ActionDefinition(
    command_type="form-ensemble",
    title="Form an ensemble",
    description="Band together with another musician under a shared ensemble name.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.MAJOR),
    arguments={
        "member_id": ActionArgument(
            title="Bandmate",
            description="The musician to band with.",
            kind="entity",
            required=True,
        ),
        "band": ActionArgument(
            title="Ensemble name",
            description="The name of the ensemble.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = [
    "FORM_ENSEMBLE_DEF",
    "BandmateOf",
    "EnsembleFormedEvent",
    "FormEnsembleHandler",
    "are_bandmates",
    "bandmates_of",
    "ensemble_fragments",
    "present_bandmates",
]
