import math

import CoolProp.CoolProp as CP
import pytest

from dynamiclh2poolx import (
    ConstantHeatFluxWaterSurface,
    DeclaredInflow,
    DynamicPoolConfig,
    DynamicPoolResult,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)


def small_numerics(**changes):
    values = dict(domain_radius_m=.5, radial_step_m=.025,
                  maximum_time_step_s=.01, source_radius_m=.1,
                  reported_front_depth_m=1e-5)
    values.update(changes)
    return ShallowLayerNumerics(**values)


def test_solid_contact_integral_is_partition_independent():
    surface = SolidSemiInfiniteSurface("test", 2.0, 2.5e-7, 282.0)
    common = (20.3, 70.9, 448_900.0)
    whole = surface.evaporated_depth_m(0.0, 10.0, *common)
    partitioned = sum(surface.evaporated_depth_m(a, b, *common)
                      for a, b in ((0., 1.), (1., 4.), (4., 10.)))
    assert partitioned == pytest.approx(whole, rel=1e-14)


def test_no_inflow_has_zero_pool():
    surface = ConstantHeatFluxWaterSurface(2e5, "unit test")
    result = run_dynamic_pool(
        DynamicPoolConfig(surface, small_numerics()),
        DeclaredInflow((0.,), (0.,)), (0., .1, .2),
    )
    assert all(row.liquid_mass_kg == 0.0 and row.radius_m == 0.0 for row in result.ledger)
    assert result.mass_balance_residual_kg == 0.0


def test_zero_heat_conserves_declared_inflow():
    pressure = 101325.0
    saturation = float(CP.PropsSI("T", "P", pressure, "Q", 0, "Hydrogen"))
    surface = SolidSemiInfiniteSurface("zero heat", 1.0, 1e-6, saturation)
    result = run_dynamic_pool(
        DynamicPoolConfig(surface, small_numerics(), pressure),
        DeclaredInflow((0.,), (.05,)), (0., .1, .2),
    )
    assert result.ledger[-1].cumulative_inflow_kg == pytest.approx(.01)
    assert result.ledger[-1].cumulative_evaporation_kg == pytest.approx(0.0, abs=1e-15)
    assert result.ledger[-1].liquid_mass_kg == pytest.approx(.01, abs=2e-6)
    assert abs(result.mass_balance_residual_kg) < 2e-6


def test_dynamic_state_is_nonnegative_and_serialisable():
    result = run_dynamic_pool(
        DynamicPoolConfig(ConstantHeatFluxWaterSurface(2e5, "unit test"),
                          small_numerics()),
        DeclaredInflow((0., .2), (.08, 0.)), (0., .1, .2, .3),
    )
    assert all(row.liquid_mass_kg >= 0 and row.radius_m >= 0 and row.mean_depth_m >= 0
               for row in result.ledger)
    loaded = DynamicPoolResult.from_dict(result.to_dict())
    assert loaded == result
    assert abs(result.mass_balance_residual_kg) < 2e-6


def test_water_and_solid_closures_remain_distinct():
    water = ConstantHeatFluxWaterSurface(2e5, "test")
    solid = SolidSemiInfiniteSurface("test", 204., 8.6e-5, 278., heat_flux_multiplier=.4)
    assert water.closure_id != solid.closure_id
    assert "water" in water.closure_id
    assert "solid" in solid.closure_id


def test_invalid_annular_source_is_rejected():
    with pytest.raises(ValueError):
        small_numerics(source_inner_radius_m=.1, source_radius_m=.1)
