"""World-generation enrichment: tag generated musicians and instruments.

Generated entities expose semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text and:

- gives a generated **musician** character a starter :class:`RepertoireComponent` (and a
  :class:`TipJarComponent` to busk into), and
- tags a generated **instrument** object with :class:`InstrumentComponent`, inferring the
  instrument kind from the same text.

The core generator never has to know this plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import (
    CharacterGeneratedEvent,
    GeneratedEntityEvent,
    ObjectGeneratedEvent,
)
from bunnyland.core.world_actor import WorldActor

from .components import InstrumentComponent, RepertoireComponent, TipJarComponent
from .reputation import aspire_to_renown

#: Words that mark a generated character as a musician who should know some songs.
MUSICIAN_TERMS = (
    "musician",
    "bard",
    "minstrel",
    "troubadour",
    "singer",
    "songstress",
    "performer",
    "busker",
    "fiddler",
    "drummer",
    "piper",
    "harpist",
    "lutenist",
    "entertainer",
)

#: Instrument kinds recognized in generated object text, most specific first. The first
#: match becomes the instrument's ``kind``.
INSTRUMENT_KINDS = (
    "fiddle",
    "violin",
    "lute",
    "harp",
    "drum",
    "flute",
    "pipe",
    "lyre",
    "mandolin",
    "banjo",
    "tambourine",
    "accordion",
    "ocarina",
)

#: Generic words that mark a generated object as an instrument of the default kind.
GENERIC_INSTRUMENT_TERMS = ("instrument", "musical")

#: The songs a generated musician starts out knowing (one uplifting, one somber).
STARTER_SONGS = ("a merry harvest jig", "lament for the fallen")


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _mentions(event: GeneratedEntityEvent, terms: tuple[str, ...]) -> bool:
    text = _text(event)
    return any(term in text for term in terms)


def _instrument_kind(event: GeneratedEntityEvent) -> str | None:
    text = _text(event)
    for kind in INSTRUMENT_KINDS:
        if kind in text:
            return kind
    if any(term in text for term in GENERIC_INSTRUMENT_TERMS):
        return "lute"
    return None


class BardWorldgenHook:
    """Attach repertoires to generated musicians and instrument components to instruments."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(CharacterGeneratedEvent, self._on_character)
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_character(self, event: CharacterGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(RepertoireComponent):
            return
        if _mentions(event, MUSICIAN_TERMS):
            replace_component(entity, RepertoireComponent(songs=STARTER_SONGS))
            if not entity.has_component(TipJarComponent):
                replace_component(entity, TipJarComponent())
            # A generated musician aspires to fame: route the goal through core persona/goals.
            aspire_to_renown(entity)

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(InstrumentComponent):
            return
        kind = _instrument_kind(event)
        if kind is not None:
            replace_component(entity, InstrumentComponent(kind=kind))


__all__ = [
    "GENERIC_INSTRUMENT_TERMS",
    "INSTRUMENT_KINDS",
    "MUSICIAN_TERMS",
    "STARTER_SONGS",
    "BardWorldgenHook",
]
