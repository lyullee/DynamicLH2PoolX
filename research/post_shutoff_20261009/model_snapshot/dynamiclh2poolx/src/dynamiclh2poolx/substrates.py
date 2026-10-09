"""Named substrate heat-transfer closures for dynamic spreading pools."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SolidSemiInfiniteSurface:
    """Semi-infinite solid conduction evaluated with local wet-contact age.

    The local heat flux is ``k (T0 - Tsat) / sqrt(pi alpha age)``.  The
    integral is evaluated analytically over each solver step, so the initial
    singularity is integrable and does not depend on the time-step size.
    """

    name: str
    conductivity_W_mK: float
    diffusivity_m2_s: float
    initial_temperature_K: float
    heat_flux_cap_W_m2: float | None = None
    heat_flux_multiplier: float = 1.0

    def __post_init__(self) -> None:
        for field, value in (
            ("conductivity_W_mK", self.conductivity_W_mK),
            ("diffusivity_m2_s", self.diffusivity_m2_s),
            ("initial_temperature_K", self.initial_temperature_K),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{field} must be finite and > 0")
        if self.heat_flux_cap_W_m2 is not None and (
            not math.isfinite(self.heat_flux_cap_W_m2)
            or self.heat_flux_cap_W_m2 <= 0.0
        ):
            raise ValueError("heat_flux_cap_W_m2 must be finite and > 0 or None")
        if (not math.isfinite(self.heat_flux_multiplier)
                or self.heat_flux_multiplier <= 0.0):
            raise ValueError("heat_flux_multiplier must be finite and > 0")

    @property
    def closure_id(self) -> str:
        return (
            "solid_local_contact_semi_infinite_v1"
            if self.heat_flux_multiplier == 1.0
            else "solid_local_contact_semi_infinite_scaled_v1"
        )

    def evaporated_depth_m(
        self,
        old_contact_age_s: float,
        new_contact_age_s: float,
        saturation_temperature_K: float,
        liquid_density_kg_m3: float,
        latent_heat_J_kg: float,
    ) -> float:
        """Return liquid-depth capacity evaporated over a contact-age step."""
        if new_contact_age_s < old_contact_age_s or old_contact_age_s < 0.0:
            raise ValueError("contact ages must be ordered and non-negative")
        if new_contact_age_s == old_contact_age_s:
            return 0.0
        delta_temperature = max(0.0, self.initial_temperature_K - saturation_temperature_K)
        coefficient = (
            self.conductivity_W_mK * delta_temperature
            / (liquid_density_kg_m3 * latent_heat_J_kg
               * math.sqrt(math.pi * self.diffusivity_m2_s))
        ) * self.heat_flux_multiplier
        if self.heat_flux_cap_W_m2 is None:
            return 2.0 * coefficient * (
                math.sqrt(new_contact_age_s) - math.sqrt(old_contact_age_s)
            )
        cap = self.heat_flux_cap_W_m2 / (liquid_density_kg_m3 * latent_heat_J_kg)
        switch_age = (coefficient / cap) ** 2 if cap > 0.0 else math.inf
        capped_end = min(new_contact_age_s, switch_age)
        capped_start = min(old_contact_age_s, switch_age)
        result = cap * max(0.0, capped_end - capped_start)
        conduction_start = max(old_contact_age_s, switch_age)
        if new_contact_age_s > conduction_start:
            result += 2.0 * coefficient * (
                math.sqrt(new_contact_age_s) - math.sqrt(conduction_start)
            )
        return result


@dataclass(frozen=True)
class ConstantHeatFluxWaterSurface:
    """Limited empirical water/ice closure for short continuous releases.

    Dienhart (JUEL-3155, 1995, section 4.2.2) permits a constant heat flux for
    roughly the first 50--60 s on water.  A value supplied here is therefore
    an experiment-specific boundary condition, not a generic solid-ground
    property and not a resolved ice-growth model.
    """

    heat_flux_W_m2: float
    calibration_label: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.heat_flux_W_m2) or self.heat_flux_W_m2 <= 0.0:
            raise ValueError("heat_flux_W_m2 must be finite and > 0")
        if not self.calibration_label.strip():
            raise ValueError("calibration_label must identify the evidence source")

    @property
    def closure_id(self) -> str:
        return "water_constant_flux_empirical_50s_v1"

    def evaporated_depth_m(
        self,
        old_contact_age_s: float,
        new_contact_age_s: float,
        saturation_temperature_K: float,
        liquid_density_kg_m3: float,
        latent_heat_J_kg: float,
    ) -> float:
        del saturation_temperature_K
        if new_contact_age_s < old_contact_age_s or old_contact_age_s < 0.0:
            raise ValueError("contact ages must be ordered and non-negative")
        return (
            self.heat_flux_W_m2 * (new_contact_age_s - old_contact_age_s)
            / (liquid_density_kg_m3 * latent_heat_J_kg)
        )
