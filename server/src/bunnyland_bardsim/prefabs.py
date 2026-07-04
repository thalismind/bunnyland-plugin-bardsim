"""Spawn factories for instruments and musicians.

The loader does not consume ``ContentContribution.prefabs``, so these ``spawn_entity``
helpers create bard content from tests, admin tooling, or a worldgen hook. Instruments are
portable, holdable items; ``spawn_musician`` makes a character who already knows some songs
and has a tip jar to busk into. Pass ``room_id`` to drop the result into a room, or leave it
out to spawn it uncontained (e.g. straight into an inventory).

The instrument catalogue is data-driven: :data:`INSTRUMENT_FAMILIES` groups every kind by
family (strings, winds, percussion, keys, folk/exotic), :func:`spawn_instrument` spawns any
kind by name, and each kind also has a named ``spawn_*`` helper collected in
:data:`INSTRUMENT_SPAWNERS`.
"""

from __future__ import annotations

from collections.abc import Callable

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

#: Every playable instrument kind, grouped by family. Kinds are the human-readable strings
#: stored on :class:`InstrumentComponent.kind` and the item's ``IdentityComponent.name``.
INSTRUMENT_FAMILIES: dict[str, tuple[str, ...]] = {
    "strings": ("lute", "fiddle", "harp", "lyre", "mandolin", "banjo"),
    "winds": ("flute", "pan pipes", "horn", "bagpipes", "ocarina"),
    "percussion": ("drum", "tambourine", "hand bells", "gong", "cymbals"),
    "keys": ("harpsichord", "hurdy-gurdy", "pipe organ", "accordion"),
    "exotic": ("sitar", "didgeridoo", "kalimba", "bodhran"),
}

#: A flat, stable tuple of every instrument kind across all families.
INSTRUMENT_KINDS = tuple(kind for kinds in INSTRUMENT_FAMILIES.values() for kind in kinds)


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


def spawn_instrument(world: World, kind: str, *, room_id=None) -> Entity:
    """Spawn an instrument of any ``kind``, optionally placed in ``room_id``."""
    return _spawn_instrument(world, kind, room_id)


# --- Strings -------------------------------------------------------------------------


def spawn_lute(world: World, *, room_id=None) -> Entity:
    """Spawn a lute, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "lute", room_id)


def spawn_fiddle(world: World, *, room_id=None) -> Entity:
    """Spawn a fiddle, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "fiddle", room_id)


def spawn_harp(world: World, *, room_id=None) -> Entity:
    """Spawn a harp, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "harp", room_id)


def spawn_lyre(world: World, *, room_id=None) -> Entity:
    """Spawn a lyre, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "lyre", room_id)


def spawn_mandolin(world: World, *, room_id=None) -> Entity:
    """Spawn a mandolin, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "mandolin", room_id)


def spawn_banjo(world: World, *, room_id=None) -> Entity:
    """Spawn a banjo, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "banjo", room_id)


# --- Winds ---------------------------------------------------------------------------


def spawn_flute(world: World, *, room_id=None) -> Entity:
    """Spawn a flute, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "flute", room_id)


def spawn_pan_pipes(world: World, *, room_id=None) -> Entity:
    """Spawn a set of pan pipes, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "pan pipes", room_id)


def spawn_horn(world: World, *, room_id=None) -> Entity:
    """Spawn a horn, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "horn", room_id)


def spawn_bagpipes(world: World, *, room_id=None) -> Entity:
    """Spawn a set of bagpipes, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "bagpipes", room_id)


def spawn_ocarina(world: World, *, room_id=None) -> Entity:
    """Spawn an ocarina, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "ocarina", room_id)


# --- Percussion ----------------------------------------------------------------------


def spawn_drum(world: World, *, room_id=None) -> Entity:
    """Spawn a drum, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "drum", room_id)


def spawn_tambourine(world: World, *, room_id=None) -> Entity:
    """Spawn a tambourine, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "tambourine", room_id)


def spawn_hand_bells(world: World, *, room_id=None) -> Entity:
    """Spawn a set of hand bells, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "hand bells", room_id)


def spawn_gong(world: World, *, room_id=None) -> Entity:
    """Spawn a gong, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "gong", room_id)


def spawn_cymbals(world: World, *, room_id=None) -> Entity:
    """Spawn a pair of cymbals, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "cymbals", room_id)


# --- Keys ----------------------------------------------------------------------------


def spawn_harpsichord(world: World, *, room_id=None) -> Entity:
    """Spawn a harpsichord, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "harpsichord", room_id)


def spawn_hurdy_gurdy(world: World, *, room_id=None) -> Entity:
    """Spawn a hurdy-gurdy, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "hurdy-gurdy", room_id)


def spawn_pipe_organ(world: World, *, room_id=None) -> Entity:
    """Spawn a pipe organ, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "pipe organ", room_id)


def spawn_accordion(world: World, *, room_id=None) -> Entity:
    """Spawn an accordion, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "accordion", room_id)


# --- Folk / exotic -------------------------------------------------------------------


def spawn_sitar(world: World, *, room_id=None) -> Entity:
    """Spawn a sitar, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "sitar", room_id)


def spawn_didgeridoo(world: World, *, room_id=None) -> Entity:
    """Spawn a didgeridoo, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "didgeridoo", room_id)


def spawn_kalimba(world: World, *, room_id=None) -> Entity:
    """Spawn a kalimba, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "kalimba", room_id)


def spawn_bodhran(world: World, *, room_id=None) -> Entity:
    """Spawn a bodhran, optionally placed in ``room_id``."""
    return _spawn_instrument(world, "bodhran", room_id)


#: A named ``spawn_*`` helper for every instrument kind, keyed by kind. Handy for
#: table-driven spawning and tests that exercise the whole catalogue.
INSTRUMENT_SPAWNERS: dict[str, Callable[..., Entity]] = {
    "lute": spawn_lute,
    "fiddle": spawn_fiddle,
    "harp": spawn_harp,
    "lyre": spawn_lyre,
    "mandolin": spawn_mandolin,
    "banjo": spawn_banjo,
    "flute": spawn_flute,
    "pan pipes": spawn_pan_pipes,
    "horn": spawn_horn,
    "bagpipes": spawn_bagpipes,
    "ocarina": spawn_ocarina,
    "drum": spawn_drum,
    "tambourine": spawn_tambourine,
    "hand bells": spawn_hand_bells,
    "gong": spawn_gong,
    "cymbals": spawn_cymbals,
    "harpsichord": spawn_harpsichord,
    "hurdy-gurdy": spawn_hurdy_gurdy,
    "pipe organ": spawn_pipe_organ,
    "accordion": spawn_accordion,
    "sitar": spawn_sitar,
    "didgeridoo": spawn_didgeridoo,
    "kalimba": spawn_kalimba,
    "bodhran": spawn_bodhran,
}


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
    "INSTRUMENT_FAMILIES",
    "INSTRUMENT_KINDS",
    "INSTRUMENT_SPAWNERS",
    "spawn_accordion",
    "spawn_bagpipes",
    "spawn_banjo",
    "spawn_bodhran",
    "spawn_cymbals",
    "spawn_didgeridoo",
    "spawn_drum",
    "spawn_fiddle",
    "spawn_flute",
    "spawn_gong",
    "spawn_hand_bells",
    "spawn_harp",
    "spawn_harpsichord",
    "spawn_horn",
    "spawn_hurdy_gurdy",
    "spawn_instrument",
    "spawn_kalimba",
    "spawn_lute",
    "spawn_lyre",
    "spawn_mandolin",
    "spawn_musician",
    "spawn_ocarina",
    "spawn_pan_pipes",
    "spawn_pipe_organ",
    "spawn_sitar",
    "spawn_tambourine",
]
