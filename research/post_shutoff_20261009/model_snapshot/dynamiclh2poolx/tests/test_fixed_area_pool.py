"""Numerical-contract tests for the bounded, nonspreading dynamic route."""

import pytest

from dynamiclh2poolx import DeclaredInflow, FixedAreaPoolConfig, run_fixed_area_pool


def test_fixed_area_pool_conserves_mass_and_serialises():
    result = run_fixed_area_pool(
        FixedAreaPoolConfig(area_m2=1.0, ambient_temperature_K=20.0),
        DeclaredInflow((0.0,), (0.5,)),
        (0.0, 2.0, 4.0),
    )
    assert result.mass_balance_residual_kg == pytest.approx(0.0, abs=1e-12)
    assert result.ledger[-1].liquid_mass_kg == pytest.approx(2.0)
    assert result.from_dict(result.to_dict()) == result


def test_empty_pool_is_nonnegative_and_input_limited():
    result = run_fixed_area_pool(
        FixedAreaPoolConfig(area_m2=1.0, initial_liquid_mass_kg=0.01),
        DeclaredInflow((0.0,), (0.0,)),
        (0.0, 60.0, 120.0),
    )
    assert all(record.liquid_mass_kg >= 0.0 for record in result.ledger)
    assert result.ledger[-1].source_status == "input_limited"


def test_inflow_changes_are_internal_boundaries():
    result = run_fixed_area_pool(
        FixedAreaPoolConfig(area_m2=1.0, ambient_temperature_K=20.0),
        DeclaredInflow((0.0, 10.0, 30.0), (0.0, 1.0, 0.0)),
        (0.0, 20.0),
    )
    assert result.ledger[-1].liquid_mass_kg == pytest.approx(10.0)


def test_analytical_uncapped_inventory_and_output_independence():
    import math
    from dynamiclh2poolx import LH2Release, evaluate_pool_source
    config = FixedAreaPoolConfig(area_m2=0.1, initial_liquid_mass_kg=100.0,
                                 critical_heat_flux_W_m2=None)
    inflow = DeclaredInflow((0.0,), (0.0,))
    coarse = run_fixed_area_pool(config, inflow, (0.0, 100.0))
    fine = run_fixed_area_pool(config, inflow, tuple(float(t) for t in range(101)))
    flux_at_one = evaluate_pool_source(LH2Release(1, 1), elapsed_s=1,
                                      critical_heat_flux_W_m2=None).evaporative_flux_kg_m2_s
    expected_loss = 2 * config.area_m2 * flux_at_one * math.sqrt(100)
    assert coarse.ledger[-1].liquid_mass_kg == pytest.approx(100 - expected_loss, abs=1e-10)
    assert fine.ledger[-1].liquid_mass_kg == pytest.approx(coarse.ledger[-1].liquid_mass_kg, abs=1e-10)


def test_empty_event_time_matches_constant_capacity_solution():
    config = FixedAreaPoolConfig(area_m2=1, initial_liquid_mass_kg=0.01,
                                 critical_heat_flux_W_m2=1000)
    result = run_fixed_area_pool(config, DeclaredInflow((0.0,), (0.0,)), (0.0, 100.0))
    rate = result.ledger[0].evaporation_rate_kg_s
    assert result.disappearance_times_s == pytest.approx((0.01 / rate,), abs=1e-9)
    assert result.ledger[-1].evaporation_rate_kg_s == 0


def test_dry_pool_can_start_accumulating_with_declining_capacity():
    from dynamiclh2poolx.conduction import ConductionCapacity
    # e=1/sqrt(t), input=1: stays empty until t=1; then M=t-2sqrt(t)+1.
    mass, event = ConductionCapacity(1, float('inf')).advance(0, 1, 0, 4)
    assert mass == pytest.approx(1.0)
    assert event is None
