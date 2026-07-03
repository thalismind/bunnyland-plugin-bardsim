"""Bardsim components: instruments, repertoires, tip jars, and performance noise.

Components are immutable; the command handlers and the performance consequence swap whole
values with ``replace_component(entity, replace(component, ...))``.

- :class:`InstrumentComponent` lives on a portable item a character can hold and play.
- :class:`RepertoireComponent` lives on a character and lists the songs they can perform.
- :class:`TipJarComponent` lives on a performer and accumulates busking coins.
- :class:`PerformanceNoiseComponent` marks the short-lived noise entity a performance
  spawns, so prompts and the consequence can find "what is playing here" without the noise
  ever living on a persistent entity.
"""

from __future__ import annotations

from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component


@dataclass(frozen=True)
class InstrumentComponent(Component):
    """A playable instrument (lute, fiddle, drum…). Sits on a portable, holdable item."""

    kind: str = "lute"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if ctx.is_first_person:
            return (f"You are holding a {self.kind}.",)
        return (f"A {self.kind} rests here.",)


@dataclass(frozen=True)
class RepertoireComponent(Component):
    """The songs a character knows and may perform."""

    songs: tuple[str, ...] = ()

    def knows(self, song: str) -> bool:
        """Whether ``song`` is in this repertoire (case-insensitive)."""
        target = song.casefold()
        return any(known.casefold() == target for known in self.songs)

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        # Only the character themselves should see their private repertoire.
        if not ctx.is_first_person or not self.songs:
            return ()
        listing = ", ".join(sorted(self.songs))
        return (f"You know how to play: {listing}.",)


@dataclass(frozen=True)
class TipJarComponent(Component):
    """A running total of busking coins a performer has earned."""

    coins: int = 0


@dataclass(frozen=True)
class PerformanceNoiseComponent(Component):
    """Marks the throwaway noise entity a performance spawns into a room."""

    song: str
    mood: str
    performer_id: str
    performer_name: str
    room_id: str


__all__ = [
    "InstrumentComponent",
    "PerformanceNoiseComponent",
    "RepertoireComponent",
    "TipJarComponent",
]
