"""Explicit liquid-to-ground inflow histories for dynamic pool routes."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DeclaredInflow:
    """Zero-order-hold liquid-to-ground inflow history.

    ``times_s`` [s] and ``rates_kg_s`` [kg s-1] have equal length.  Each rate
    applies from its timestamp until the next timestamp; the last rate applies
    thereafter.  This is a declared ground-inflow boundary, not a jet-impact
    or deposition model.
    """

    times_s: tuple[float, ...]
    rates_kg_s: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.times_s:
            raise ValueError("times_s must contain at least one timestamp")
        if len(self.times_s) != len(self.rates_kg_s):
            raise ValueError("times_s and rates_kg_s must have equal length")
        if self.times_s[0] != 0.0:
            raise ValueError("the first inflow timestamp must be 0 s")
        if any(not math.isfinite(value) or value < 0.0 for value in self.rates_kg_s):
            raise ValueError("rates_kg_s must be finite and >= 0")
        if any(not math.isfinite(value) or value < 0.0 for value in self.times_s):
            raise ValueError("times_s must be finite and >= 0")
        if any(right <= left for left, right in zip(self.times_s, self.times_s[1:])):
            raise ValueError("times_s must be strictly increasing")

    def rate_at(self, time_s: float) -> float:
        """Return the declared liquid-to-ground rate [kg s-1] at ``time_s``."""
        if not math.isfinite(time_s) or time_s < 0.0:
            raise ValueError("time_s must be finite and >= 0")
        selected = self.rates_kg_s[0]
        for timestamp, rate in zip(self.times_s, self.rates_kg_s):
            if timestamp > time_s:
                break
            selected = rate
        return selected
