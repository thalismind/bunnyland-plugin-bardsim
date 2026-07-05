"""Reputation logic: accruing renown, naming a standing, and the renowned-performer goal.

The :class:`~bunnyland_bardsim.connectors.Reputation` component is the shared surface; this
module is the behaviour around it. Renown accrues from gigs and compositions, maps to a
human-readable standing tier, and — once a performer crosses :data:`FAME_THRESHOLD` — marks a
famous act the gig consequence turns into a storyteller incident.

The renowned-performer **goal** routes through the core ``GoalComponent`` (persona/goals),
never a bardsim-specific field, so a bard's ambition surfaces in the same foundation prompt as
every other character's goals.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import contents
from bunnyland.core.components import IdentityComponent
from bunnyland.core.ecs import replace_component
from bunnyland.mechanics.persona import GoalComponent
from relics import Entity, EntityId, World

from .connectors import Reputation
from .spatial import room_of

#: Renown thresholds, ascending, paired with the standing they name.
STANDING_TIERS: tuple[tuple[int, str], ...] = (
    (100, "renowned"),
    (50, "celebrated"),
    (20, "notable"),
    (5, "known"),
    (0, "unknown"),
)

#: Renown at or above which a performer is famous enough to draw a crowd (a storyteller
#: incident). Matches the "renowned" standing tier.
FAME_THRESHOLD = 100

#: The active goal a would-be star carries, routed through the core ``GoalComponent``.
RENOWNED_GOAL = "become a renowned performer"


def standing(renown: int) -> str:
    """Name the standing a given ``renown`` total reads as."""
    for threshold, label in STANDING_TIERS:
        if renown >= threshold:
            return label
    return "unknown"


def reputation_of(world: World, character_id: EntityId) -> Reputation | None:
    """Return a character's :class:`Reputation`, or ``None`` if they have none yet."""
    if not world.has_entity(character_id):
        return None
    character = world.get_entity(character_id)
    if not character.has_component(Reputation):
        return None
    return character.get_component(Reputation)


def grant_renown(world: World, character_id: EntityId, amount: int) -> Reputation | None:
    """Add ``amount`` renown to a character (creating the surface), clamped at zero.

    Returns the updated :class:`Reputation`, or ``None`` if the character does not exist.
    """
    if not world.has_entity(character_id):
        return None
    character = world.get_entity(character_id)
    current = (
        character.get_component(Reputation)
        if character.has_component(Reputation)
        else Reputation()
    )
    updated = replace(current, renown=max(0, current.renown + amount))
    replace_component(character, updated)
    return updated


def is_famous(reputation: Reputation | None) -> bool:
    """Whether a reputation has reached the crowd-drawing :data:`FAME_THRESHOLD`."""
    return reputation is not None and reputation.renown >= FAME_THRESHOLD


def aspire_to_renown(character: Entity) -> None:
    """Give a character the renowned-performer goal via the core ``GoalComponent``."""
    current = (
        character.get_component(GoalComponent)
        if character.has_component(GoalComponent)
        else GoalComponent()
    )
    if RENOWNED_GOAL in current.active_goals:
        return
    replace_component(
        character, replace(current, active_goals=(*current.active_goals, RENOWNED_GOAL))
    )


def reputation_fragments(world: World, character: Entity) -> list[str]:
    """Foundation-prompt lines: your own standing (first person) and famous room-mates.

    The provider is always invoked for the viewer's own entity, so the standing line is
    first-person. Any *other* renowned performer sharing the room is named in the third
    person, so a bystander reads the room's celebrity without seeing their private renown.
    """
    lines: list[str] = []
    if character.has_component(Reputation):
        renown = character.get_component(Reputation).renown
        if renown > 0:
            lines.append(f"Your standing as a performer is {standing(renown)} (renown {renown}).")
    room = room_of(world, character.id)
    if room is not None:
        for occupant_id in contents(room):
            if occupant_id == character.id or not world.has_entity(occupant_id):
                continue
            other = world.get_entity(occupant_id)
            if not other.has_component(Reputation) or not other.has_component(IdentityComponent):
                continue
            if is_famous(other.get_component(Reputation)):
                name = other.get_component(IdentityComponent).name
                lines.append(f"{name} is a renowned performer.")
    return sorted(lines)


__all__ = [
    "FAME_THRESHOLD",
    "RENOWNED_GOAL",
    "STANDING_TIERS",
    "aspire_to_renown",
    "grant_renown",
    "is_famous",
    "reputation_fragments",
    "reputation_of",
    "standing",
]
