"""Declarative musician and instrument generation enrichment."""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import InstrumentComponent, RepertoireComponent, TipJarComponent
from .reputation import RENOWNED_GOAL

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
GENERIC_INSTRUMENT_TERMS = ("instrument", "musical")
STARTER_SONGS = ("a merry harvest jig", "lament for the fallen")
PERSONA_GOALS_CAPABILITY = "bunnyland.persona.goals"
PERSONA_GOALS_CONTEXT = "bunnyland.persona.active_goals"


def _text(request: GenerationRequest) -> str:
    return " ".join(
        (request.source_key, request.entity_kind, request.description, *request.tags)
    ).casefold()


def _is_musician(request: GenerationRequest) -> bool:
    text = _text(request)
    return request.entity_kind == "character" and any(term in text for term in MUSICIAN_TERMS)


class BardGenerationNormalizer:
    """Request Foundation Persona's goal surface for generated musicians."""

    def normalize(self, request: GenerationRequest) -> GenerationRequest:
        if not _is_musician(request):
            return request
        goals = tuple(request.context.get(PERSONA_GOALS_CONTEXT, ()))
        return replace(
            request,
            capabilities=tuple(dict.fromkeys((*request.capabilities, PERSONA_GOALS_CAPABILITY))),
            context={
                **request.context,
                PERSONA_GOALS_CONTEXT: tuple(dict.fromkeys((*goals, RENOWNED_GOAL))),
            },
        )


class BardGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        existing = tuple(request.context.get("base_components", ()))
        if _is_musician(request):
            components = []
            if not any(isinstance(item, RepertoireComponent) for item in existing):
                components.append(RepertoireComponent(songs=STARTER_SONGS))
            if not any(isinstance(item, TipJarComponent) for item in existing):
                components.append(TipJarComponent())
            return GenerationDelta(components=tuple(components))
        if request.entity_kind == "room" or any(
            isinstance(item, InstrumentComponent) for item in existing
        ):
            return GenerationDelta()
        text = _text(request)
        kind = next((kind for kind in INSTRUMENT_KINDS if kind in text), None)
        if kind is None and any(term in text for term in GENERIC_INSTRUMENT_TERMS):
            kind = "lute"
        return GenerationDelta(
            components=(InstrumentComponent(kind=kind),) if kind is not None else ()
        )


__all__ = [
    "BardGenerationEnricher",
    "BardGenerationNormalizer",
    "GENERIC_INSTRUMENT_TERMS",
    "INSTRUMENT_KINDS",
    "MUSICIAN_TERMS",
    "STARTER_SONGS",
]
