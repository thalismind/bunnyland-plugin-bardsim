from __future__ import annotations

import pytest
from bunnyland.core import (
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    RoomComponent,
    WorldActor,
    contents,
    spawn_entity,
)

from bunnyland_bardsim import (
    InstrumentComponent,
    spawn_instrument,
    spawn_musician,
)
from bunnyland_bardsim.prefabs import (
    INSTRUMENT_FAMILIES,
    INSTRUMENT_KINDS,
    INSTRUMENT_SPAWNERS,
)


def test_catalogue_is_internally_consistent():
    # The flat kind tuple, the family grouping, and the named-spawner registry must all
    # describe exactly the same instruments.
    from_families = tuple(kind for kinds in INSTRUMENT_FAMILIES.values() for kind in kinds)
    assert INSTRUMENT_KINDS == from_families
    assert set(INSTRUMENT_SPAWNERS) == set(INSTRUMENT_KINDS)
    # No duplicate kinds across families.
    assert len(INSTRUMENT_KINDS) == len(set(INSTRUMENT_KINDS))


def test_families_cover_the_expected_ranges():
    assert set(INSTRUMENT_FAMILIES) == {
        "strings",
        "winds",
        "percussion",
        "keys",
        "exotic",
    }
    # Every family contributes several instruments.
    for kinds in INSTRUMENT_FAMILIES.values():
        assert len(kinds) >= 3


@pytest.mark.parametrize("kind,spawner", sorted(INSTRUMENT_SPAWNERS.items()))
def test_named_spawner_builds_a_playable_instrument(kind, spawner):
    actor = WorldActor()
    item = spawner(actor.world)

    assert item.get_component(InstrumentComponent).kind == kind
    assert item.get_component(IdentityComponent).name == kind
    assert item.has_component(PortableComponent)
    assert item.get_component(HoldableComponent).slot == "hand"


@pytest.mark.parametrize("kind", INSTRUMENT_KINDS)
def test_generic_spawn_instrument_covers_every_kind(kind):
    actor = WorldActor()
    item = spawn_instrument(actor.world, kind)
    assert item.get_component(InstrumentComponent).kind == kind


def test_instrument_can_be_dropped_into_a_room():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Hall")])
    harp = spawn_instrument(actor.world, "harp", room_id=room.id)

    assert harp.id in contents(room)


def test_spawn_instrument_ignores_a_missing_room():
    actor = WorldActor()
    # A room id that does not exist should not raise; the item is simply uncontained.
    ghost_room = spawn_entity(actor.world, [RoomComponent(title="Gone")])
    ghost_id = ghost_room.id
    actor.world.remove(ghost_id)

    item = spawn_instrument(actor.world, "drum", room_id=ghost_id)
    assert item.get_component(InstrumentComponent).kind == "drum"


def test_spawn_musician_knows_requested_songs_and_can_busk():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Corner")])
    songs = ("a moonlight serenade", "the iron battle march")
    bard = spawn_musician(actor.world, name="Tam", room_id=room.id, songs=songs)

    assert bard.id in contents(room)
    from bunnyland_bardsim import RepertoireComponent, TipJarComponent

    assert bard.get_component(RepertoireComponent).songs == songs
    assert bard.get_component(TipJarComponent).coins == 0
