"""Player/AI verbs: ``perform`` a known song and ``learn-song`` to grow a repertoire.

``perform`` acts on an instrument the character is **holding** and a song already in their
:class:`RepertoireComponent`. It fills the current room with a short-lived noise entity
(carrying a :class:`PerformanceNoiseComponent`) so the core hearing pipeline delivers the
tune, and ensures the performer has a :class:`TipJarComponent` so the performance
consequence can pay busking tips. Validation order matches the project convention: invalid
id -> missing entity -> not held -> wrong kind -> missing/invalid argument -> invalid state.

``learn-song`` just grows the character's repertoire; you can only ever perform what you
have learned.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import NoiseComponent, spawn_entity
from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.components import IdentityComponent
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_entity,
)

from .components import (
    InstrumentComponent,
    PerformanceNoiseComponent,
    RepertoireComponent,
    TipJarComponent,
)
from .events import PerformedEvent, SongLearnedEvent
from .songs import song_mood
from .spatial import holder_of, room_of

#: A performance's noise loudness. Comfortably above the default ``HearingComponent``
#: sensitivity of ``1.0`` so listeners actually hear it.
PERFORMANCE_LOUDNESS = 3.0

#: How long a performance's noise entity lives, in epoch (world-second) units.
PERFORMANCE_TTL = 60


def _room_id(ctx: HandlerContext, entity_id) -> str | None:
    room = room_of(ctx.world, entity_id)
    return str(room.id) if room is not None else None


def _name_of(entity) -> str:
    if entity.has_component(IdentityComponent):
        return entity.get_component(IdentityComponent).name
    return "someone"


class PerformHandler:
    """Play a known song on a held instrument, filling the room with an audible tune."""

    command_type = "perform"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        item_id, item, rejection = require_entity(
            ctx,
            command.payload.get("item_id"),
            invalid_reason="invalid item id",
            missing_reason="item does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, item_id)
        if holder is None or holder.id != character_id:
            return rejected("you are not holding that instrument")
        if not item.has_component(InstrumentComponent):
            return rejected("that is not an instrument")
        song = str(command.payload.get("song", "")).strip()
        if not song:
            return rejected("you need to name a song to perform")
        repertoire = (
            character.get_component(RepertoireComponent)
            if character.has_component(RepertoireComponent)
            else None
        )
        if repertoire is None or not repertoire.knows(song):
            return rejected("you do not know that song")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("there is no room to perform in")

        mood = song_mood(song)
        self._spawn_performance(ctx, character, str(room.id), item_id, song, mood)
        self._ensure_tip_jar(character)
        return ok(
            PerformedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(item_id),),
                    item_id=str(item_id),
                    song=song,
                    mood=mood,
                )
            )
        )

    def _spawn_performance(self, ctx, character, room_id, item_id, song, mood) -> None:
        spawn_entity(
            ctx.world,
            [
                NoiseComponent(
                    loudness=PERFORMANCE_LOUDNESS,
                    text=song,
                    source_entity_id=str(item_id),
                    room_id=room_id,
                    created_at_epoch=ctx.epoch,
                    expires_at_epoch=ctx.epoch + PERFORMANCE_TTL,
                ),
                PerformanceNoiseComponent(
                    song=song,
                    mood=mood,
                    performer_id=str(character.id),
                    performer_name=_name_of(character),
                    room_id=room_id,
                ),
            ],
        )

    def _ensure_tip_jar(self, character) -> None:
        if not character.has_component(TipJarComponent):
            replace_component(character, TipJarComponent())


class LearnSongHandler:
    """Add a song to the character's repertoire."""

    command_type = "learn-song"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_entity(
            ctx,
            command.character_id,
            invalid_reason="invalid character id",
            missing_reason="character does not exist",
        )
        if rejection is not None:
            return rejection
        song = str(command.payload.get("song", "")).strip()
        if not song:
            return rejected("you need to name a song to learn")
        current = (
            character.get_component(RepertoireComponent)
            if character.has_component(RepertoireComponent)
            else RepertoireComponent()
        )
        if current.knows(song):
            return rejected("you already know that song")
        replace_component(character, replace(current, songs=(*current.songs, song)))
        return ok(
            SongLearnedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=_room_id(ctx, character_id),
                    song=song,
                )
            )
        )


PERFORM_DEF = ActionDefinition(
    command_type="perform",
    title="Perform a song",
    description="Play a song you know on an instrument you are holding.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "item_id": ActionArgument(
            title="Instrument",
            description="The instrument to play.",
            kind="entity",
            required=True,
        ),
        "song": ActionArgument(
            title="Song",
            description="A song from your repertoire to perform.",
            kind="string",
            required=True,
        ),
    },
)

LEARN_DEF = ActionDefinition(
    command_type="learn-song",
    title="Learn a song",
    description="Add a song to your repertoire so you can perform it later.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "song": ActionArgument(
            title="Song",
            description="The title of the song to learn.",
            kind="string",
            required=True,
        ),
    },
)

BARD_ACTION_DEFINITIONS = (PERFORM_DEF, LEARN_DEF)
BARD_ACTION_HANDLERS = (PerformHandler, LearnSongHandler)


__all__ = [
    "BARD_ACTION_DEFINITIONS",
    "BARD_ACTION_HANDLERS",
    "LEARN_DEF",
    "PERFORM_DEF",
    "PERFORMANCE_LOUDNESS",
    "PERFORMANCE_TTL",
    "LearnSongHandler",
    "PerformHandler",
]
