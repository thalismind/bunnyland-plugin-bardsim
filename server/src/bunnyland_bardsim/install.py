"""Runtime wiring: register the performance consequence on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .performance import PerformanceConsequence


def install_bardsim(actor: WorldActor) -> None:
    """Register the per-tick performance consequence (a ``service_factories`` entry)."""
    actor.register_consequence(PerformanceConsequence())


__all__ = ["install_bardsim"]
