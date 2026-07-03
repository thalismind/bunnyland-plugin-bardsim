"""Prompt fragment provider.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. It surfaces three things:

- **What is currently playing** in the character's room (from any live
  :class:`PerformanceNoiseComponent`).
- **Nearby instruments** — carried by the character or resting in the room.
- **Your own repertoire** — rendered first person, so only the character sees their song
  list.

An instrument component lives on the *item* entity, not the character, so — exactly as the
detector packs do — we view "from" a held instrument to make its context first-person for
the holder while bystanders (and anyone near a floor-resting instrument) read the
third-person line.
"""

from __future__ import annotations

from bunnyland.core import reachable_ids
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from relics import Entity, World

from .components import InstrumentComponent, PerformanceNoiseComponent, RepertoireComponent
from .spatial import holder_of, room_of


def bardsim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    base = ComponentPromptContext.for_entity(world, character)

    room = room_of(world, character.id)
    if room is not None:
        room_key = str(room.id)
        for performance in world.query().with_all([PerformanceNoiseComponent]).execute_entities():
            comp = performance.get_component(PerformanceNoiseComponent)
            if comp.room_id != room_key:
                continue
            if comp.performer_id == str(character.id):
                lines.append(f'You are playing "{comp.song}" here.')
            else:
                lines.append(f'{comp.performer_name} is playing "{comp.song}" here.')

    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not entity.has_component(InstrumentComponent):
            continue
        held = holder_of(world, entity_id)
        first_person = held is not None and held.id == character.id
        perspective = PromptPerspective(viewer=entity if first_person else character)
        ctx = ComponentPromptContext.for_entity(
            world, entity, perspective=perspective, room=base.room, target=character
        )
        lines.extend(entity.get_component(InstrumentComponent).prompt_fragments(ctx))

    if character.has_component(RepertoireComponent):
        lines.extend(character.get_component(RepertoireComponent).prompt_fragments(base))

    return sorted(dict.fromkeys(lines))


__all__ = ["bardsim_fragments"]
