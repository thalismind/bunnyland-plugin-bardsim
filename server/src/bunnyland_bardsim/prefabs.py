"""Spawn factories for instruments and musicians.

The loader does not consume ``ContentContribution.prefabs``, so these ``spawn_entity``
helpers create bard content from tests, admin tooling, or a worldgen hook. Instruments are
portable, holdable items; ``spawn_musician`` makes a character who already knows some songs
and has a tip jar to busk into. Pass ``room_id`` to drop the result into a room, or leave it
out to spawn it uncontained (e.g. straight into an inventory).
"""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from relics import Entity, World

from .components import InstrumentComponent, RepertoireComponent, TipJarComponent

#: Songs a spawned musician starts out knowing (one uplifting, one somber).
DEFAULT_SONGS = ("a merry harvest jig", "lament for the fallen")


def _link_into_room(world: World, entity: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(
        Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id
    )


def _spawn_instrument(world: World, kind: str, room_id) -> Entity:
    item = spawn_entity(
        world,
        [
            IdentityComponent(name=kind, kind="item", tags=("bardsim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            InstrumentComponent(kind=kind),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_lute(world: World, *, room_id=None) -> Entity:
    """Spawn a lute, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "lute", room_id)


def spawn_fiddle(world: World, *, room_id=None) -> Entity:
    """Spawn a fiddle, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "fiddle", room_id)


def spawn_drum(world: World, *, room_id=None) -> Entity:
    """Spawn a drum, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "drum", room_id)


def spawn_musician(world: World, *, name: str = "busker", room_id=None, songs=DEFAULT_SONGS
                   ) -> Entity:
    """Spawn a musician character who knows ``songs`` and has an empty tip jar."""
    character = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="character", tags=("bardsim",)),
            CharacterComponent(),
            RepertoireComponent(songs=tuple(songs)),
            TipJarComponent(),
        ],
    )
    _link_into_room(world, character, room_id)
    return character


__all__ = [
    "DEFAULT_SONGS",
    "spawn_drum",
    "spawn_fiddle",
    "spawn_lute",
    "spawn_musician",
]
