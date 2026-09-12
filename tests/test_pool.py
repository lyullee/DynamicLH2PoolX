import math

import pytest

from dynamiclh2poolx import LH2Release, evaluate_pool_source, flash_vapour_fraction


def test_flash_rises_with_storage_pressure():
    values = [flash_vapour_fraction(p) for p in (0.8, 2.0, 6.0)]
    assert values[0] < values[1] < values[2]


def test_unconfined_source_closes_the_mass_balance():
    source = evaluate_pool_source(LH2Release(0.1055, 1.0), elapsed_s=300.0)
    assert source.source_status == "quasi_steady_equilibrium"
    assert source.evaporation_rate_kg_s == pytest.approx(
        source.liquid_to_ground_kg_s)


def test_radius_scales_with_deposition_fraction():
    full = evaluate_pool_source(LH2Release(0.1055, 1.0, 1.0), elapsed_s=300.0)
    quarter = evaluate_pool_source(LH2Release(0.1055, 1.0, 0.25), elapsed_s=300.0)
    assert quarter.radius_m / full.radius_m == pytest.approx(0.5)


def test_confinement_reports_accumulation():
    source = evaluate_pool_source(LH2Release(9.5, 0.1, max_radius_m=0.5),
                                  elapsed_s=300.0)
    assert source.confined
    assert source.liquid_accumulation_rate_kg_s > 0.0


def test_bad_deposition_fraction_is_rejected():
    with pytest.raises(ValueError):
        LH2Release(1.0, 1.0, 1.1)
