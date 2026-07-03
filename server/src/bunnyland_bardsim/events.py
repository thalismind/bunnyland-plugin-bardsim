"""Domain events emitted by the bardsim verbs."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class PerformedEvent(DomainEvent):
    """A character played a song on an instrument they were holding."""

    item_id: str
    song: str
    mood: str


class SongLearnedEvent(DomainEvent):
    """A character added a song to their repertoire."""

    song: str


__all__ = ["PerformedEvent", "SongLearnedEvent"]
