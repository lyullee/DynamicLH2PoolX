"""Analytical integral of the declared solid conduction/CHF-cap closure.

q(a)=min(k*(T0-Tsat)/sqrt(pi*alpha*a), qcap), where a is
the declared substrate thermal age [s]. Constant properties, perfect thermal
contact and a semi-infinite solid are assumed. A cap is an imposed limit,
not a boiling-regime model. See Verfondern & Dienhart, ICHS 2005, Eq. (2).
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ConductionCapacity:
    coefficient_kg_sqrt_s: float
    cap_kg_s: float

    def rate(self, age_s: float) -> float:
        if self.coefficient_kg_sqrt_s == 0:
            return 0.0
        if age_s == 0:
            return self.cap_kg_s
        return min(self.cap_kg_s, self.coefficient_kg_sqrt_s / math.sqrt(age_s))

    def integral(self, start_s: float, end_s: float) -> float:
        """Potential evaporated mass [kg], analytically integrated."""
        c = self.coefficient_kg_sqrt_s
        if c == 0 or end_s == start_s:
            return 0.0
        switch = (c / self.cap_kg_s) ** 2
        flat_end = min(end_s, switch)
        flat = self.cap_kg_s * max(0.0, flat_end - start_s) if switch else 0.0
        a = max(start_s, switch)
        # Rationalisation avoids subtraction of nearly equal square roots.
        tail = 2 * c * (end_s - a) / (math.sqrt(end_s) + math.sqrt(a)) if end_s > a else 0.0
        return flat + tail

    def advance(self, mass: float, inflow: float, start: float, end: float):
        """Exact reflected mass balance, plus a bracketed dry-out age.

        Potential loss decreases monotonically. The unconstrained inventory
        is convex, and attains its minimum when capacity equals inflow.
        If that minimum is negative, locate the first zero by bisection,
        hold inventory at zero until the minimum, then resume accumulation.
        """
        def inventory(t):
            return mass + inflow * (t - start) - self.integral(start, t)
        if inflow == 0:
            minimum_at = end
        elif inflow >= self.cap_kg_s:
            minimum_at = start
        else:
            minimum_at = min(end, max(start, (self.coefficient_kg_sqrt_s / inflow) ** 2))
        lowest = inventory(minimum_at)
        if lowest > 0 or minimum_at == start:
            return max(0.0, inventory(end)), None
        event = None
        if mass > 0:
            lo, hi = start, minimum_at
            for _ in range(80):
                mid = (lo + hi) / 2
                if inventory(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            event = (lo + hi) / 2
        final = inflow * (end - minimum_at) - self.integral(minimum_at, end)
        return max(0.0, final), event
