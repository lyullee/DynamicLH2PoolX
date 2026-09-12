"""Stage-A numerical contract tests for the preserved quasi-steady API."""

import dataclasses
import math

import pytest

from dynamiclh2poolx import (
    CONCRETE_CRYOGENIC,
    LH2Release,
    PoolSource,
    Substrate,
    evaluate_pool_source,
    quasi_steady,
)
from dynamiclh2poolx.pool import _ground_flux


def test_quasi_steady_alias_preserves_v01_result_schema():
    release = LH2Release(0.1055, 1.0)
    old_name = evaluate_pool_source(release, elapsed_s=300.0)
    compatibility_route = quasi_steady(release, elapsed_s=300.0)
    assert isinstance(compatibility_route, PoolSource)
    assert dataclasses.asdict(compatibility_route) == dataclasses.asdict(old_name)


def test_quasi_steady_mass_balance_is_closed_when_unconfined():
    source = quasi_steady(LH2Release(0.1055, 1.0), elapsed_s=300.0)
    assert source.evaporation_rate_kg_s + source.liquid_accumulation_rate_kg_s == pytest.approx(
        source.liquid_to_ground_kg_s, rel=1e-12, abs=1e-15
    )


def test_zero_temperature_driving_force_is_not_silently_divided_by_zero():
    with pytest.raises(ValueError, match="equilibrium area is undefined"):
        evaluate_pool_source(
            LH2Release(0.1055, 1.0),
            elapsed_s=300.0,
            ambient_temperature_K=20.0,
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: LH2Release(float("nan"), 1.0),
        lambda: LH2Release(1.0, float("inf")),
        lambda: Substrate("", 2.0, 2.5e-7),
        lambda: Substrate("bad", 0.0, 2.5e-7),
        lambda: Substrate("bad", 2.0, -1.0),
    ],
)
def test_nonphysical_public_inputs_are_rejected(factory):
    with pytest.raises(ValueError):
        factory()


def test_semi_infinite_conduction_flux_decreases_with_elapsed_time():
    early = _ground_flux(
        substrate=CONCRETE_CRYOGENIC,
        latent_heat_J_kg=4.5e5,
        ambient_temperature_K=282.0,
        pool_temperature_K=20.0,
        elapsed_s=1.0,
        critical_heat_flux_W_m2=None,
    )
    late = _ground_flux(
        substrate=CONCRETE_CRYOGENIC,
        latent_heat_J_kg=4.5e5,
        ambient_temperature_K=282.0,
        pool_temperature_K=20.0,
        elapsed_s=4.0,
        critical_heat_flux_W_m2=None,
    )
    assert early == pytest.approx(2.0 * late)
    assert math.isfinite(early)
