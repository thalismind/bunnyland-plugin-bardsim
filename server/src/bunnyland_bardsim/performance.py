"""Performance consequence: shift listener mood and pay busking tips.

Runs each tick (registered via :func:`bunnyland_bardsim.install.install_bardsim`). A
``perform`` command spawns a short-lived noise entity carrying a
:class:`PerformanceNoiseComponent`; this consequence *resolves* each such performance
exactly once by:

1. finding every character listening in the performance's room (the audience, minus the
   performer),
2. applying the song's mood :class:`AffectDelta` to each listener's ``AffectComponent``, and
3. paying the performer tips scaled by audience size and each listener's ``SocialBond``.

Resolving once — keyed by the noise entity's id, mirroring the "seen" bookkeeping used by
other passive sims — keeps the outcome deterministic no matter how many ticks the noise
lives for. The noise entity itself is expired and removed by the core ``HearingConsequence``.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import contents
from bunnyland.core.components import AffectComponent, CharacterComponent
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import DomainEvent
from bunnyland.foundation.affect.mechanics import apply_delta, labels_for
from bunnyland.foundation.social.mechanics import bond_between
from relics import World

from .components import PerformanceNoiseComponent, TipJarComponent
from .songs import MOOD_DELTAS, tip_for_listener


class PerformanceConsequence:
    """Apply mood shifts and tips for each performance, once, when first observed."""

    def __init__(self) -> None:
        # Ids of performance noise entities already resolved, so a performance that lingers
        # for many ticks only lands its mood/tip effect a single time.
        self._resolved: set[str] = set()

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        seen: set[str] = set()
        for performance in list(
            world.query().with_all([PerformanceNoiseComponent]).execute_entities()
        ):
            key = str(performance.id)
            seen.add(key)
            if key in self._resolved:
                continue
            self._resolve(world, performance.get_component(PerformanceNoiseComponent))
            self._resolved.add(key)
        # Forget performances whose noise entity is gone so the set cannot grow forever.
        self._resolved &= seen
        return []

    def _resolve(self, world: World, performance: PerformanceNoiseComponent) -> None:
        room_id = parse_entity_id(performance.room_id)
        if room_id is None or not world.has_entity(room_id):
            return
        delta = MOOD_DELTAS.get(performance.mood)
        performer_id = parse_entity_id(performance.performer_id)
        tips = 0
        room = world.get_entity(room_id)
        for occupant_id in contents(room):
            if not world.has_entity(occupant_id) or occupant_id == performer_id:
                continue
            listener = world.get_entity(occupant_id)
            if not listener.has_component(CharacterComponent):
                continue
            if delta is not None and listener.has_component(AffectComponent):
                self._shift_mood(listener, delta)
            bond = (
                bond_between(world, occupant_id, performer_id) if performer_id is not None else None
            )
            tips += tip_for_listener(bond)
        self._pay_tips(world, performer_id, tips)

    def _shift_mood(self, listener, delta) -> None:
        affect = listener.get_component(AffectComponent)
        current = apply_delta(affect.current, delta)
        replace_component(listener, replace(affect, current=current, labels=labels_for(current)))

    def _pay_tips(self, world: World, performer_id, tips: int) -> None:
        if performer_id is None or tips <= 0 or not world.has_entity(performer_id):
            return
        performer = world.get_entity(performer_id)
        if not performer.has_component(TipJarComponent):
            return
        jar = performer.get_component(TipJarComponent)
        replace_component(performer, replace(jar, coins=jar.coins + tips))


__all__ = ["PerformanceConsequence"]
