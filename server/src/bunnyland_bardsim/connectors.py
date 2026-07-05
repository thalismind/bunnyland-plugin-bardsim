"""Cross-pack connector surfaces bardsim publishes and consumes.

bardsim owns two open surfaces any other pack may read without depending on bardsim's code:

- :class:`Reputation` — a character's shared performing **standing** (``renown``). Gigs and
  compositions accrue it; the museum (or anyone) may fold it into their own odds. This is the
  ``Reputation`` connector named in the v2 roadmap.
- :class:`ContestEntryComponent` — a **submittable performance** a gig publishes so a festival
  pack can host it as a competition entry. Publishing is self-contained: bardsim spawns the
  entry entity itself; a festival simply queries for it when present.

Consumption is safe and optional. :func:`external_reputation_bonus` reads another pack's
reputation contribution through a bare conditional import, so bardsim runs standalone: when
the partner pack is not loaded the import fails and the synergy is simply off.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Component, EntityId, World


@dataclass(frozen=True)
class Reputation(Component):
    """A character's shared performing standing (the ``Reputation`` connector surface)."""

    renown: int = 0


@dataclass(frozen=True)
class ContestEntryComponent(Component):
    """A published performance a festival pack can host as a competition entry."""

    entry_kind: str = "gig"
    performer_id: str = ""
    performer_name: str = ""
    song: str = ""
    mood: str = ""
    venue_id: str = ""
    venue_name: str = ""
    score: int = 0
    created_at_epoch: int = 0


def contest_entries(world: World) -> list[ContestEntryComponent]:
    """Every published :class:`ContestEntryComponent`, for a festival host to draw from."""
    return [
        entity.get_component(ContestEntryComponent)
        for entity in world.query().with_all([ContestEntryComponent]).execute_entities()
    ]


def external_reputation_bonus(world: World, character_id: EntityId) -> int:
    """Fold an optional partner pack's reputation into a performer's draw.

    Uses a bare conditional import: if no partner pack publishes donor renown, the import
    fails and the synergy stays off (bonus ``0``), so bardsim runs standalone.
    """
    try:
        from bunnyland_museumsim.connectors import donor_renown
    except ImportError:
        return 0
    return int(donor_renown(world, character_id))


__all__ = [
    "ContestEntryComponent",
    "Reputation",
    "contest_entries",
    "external_reputation_bonus",
]
