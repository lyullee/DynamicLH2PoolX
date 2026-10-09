import CoolProp.CoolProp as CP
import pytest

from dynamiclh2poolx import (
    ConstantHeatFluxWaterSurface,
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)


def numerics(**changes):
    values = dict(
        domain_radius_m=0.5,
        radial_step_m=0.025,
        maximum_time_step_s=0.01,
        source_radius_m=0.1,
        dry_depth_m=1.0e-8,
        reported_front_depth_m=1.0e-5,
    )
    values.update(changes)
    return ShallowLayerNumerics(**values)


def zero_heat_surface():
    saturation = float(
        CP.PropsSI("T", "P", 101325.0, "Q", 0, "Hydrogen")
    )
    return SolidSemiInfiniteSurface("zero heat", 1.0, 1.0e-6, saturation)


def test_sub_dry_inflow_remains_in_conserved_inventory():
    result = run_dynamic_pool(
        DynamicPoolConfig(zero_heat_surface(), numerics()),
        DeclaredInflow((0.0,), (1.0e-7,)),
        (0.0, 1.0),
    )
    final = result.ledger[-1]
    assert final.cumulative_inflow_kg == pytest.approx(1.0e-7)
    assert final.liquid_mass_kg == pytest.approx(1.0e-7, rel=1.0e-12)
    assert final.cumulative_numerical_mass_adjustment_kg == 0.0
    assert abs(final.unledgered_mass_residual_kg) <= 1.0e-20
    assert abs(result.mass_balance_residual_kg) <= 1.0e-20


def test_state_area_is_separate_from_reported_front_area():
    result = run_dynamic_pool(
        DynamicPoolConfig(
            ConstantHeatFluxWaterSurface(1.0e3, "test"),
            numerics(reported_front_depth_m=0.1),
        ),
        DeclaredInflow((0.0, 1.0), (1.0, 0.0)),
        (0.0, 1.0),
    )
    final = result.ledger[-1]
    assert final.liquid_mass_kg > 0.0
    assert final.wet_area_m2 > 0.0
    assert final.wet_area_mean_depth_m > 0.0
    assert final.wet_area_mean_evaporation_flux_kg_m2_s > 0.0
    assert final.substrate_heat_flux_W_m2 > 0.0
    assert final.reported_radius_m == final.radius_m == 0.0
    assert final.reported_area_m2 == final.area_m2 == 0.0


def test_invalid_surface_is_rejected_at_configuration_boundary():
    with pytest.raises(TypeError, match="surface must be"):
        DynamicPoolConfig(object())  # type: ignore[arg-type]


def test_invalid_evaporation_momentum_closure_is_rejected():
    with pytest.raises(ValueError, match="momentum_closure"):
        DynamicPoolConfig(
            zero_heat_surface(),
            numerics(),
            evaporation_momentum_closure="fit_the_data",  # type: ignore[arg-type]
        )


def test_invalid_surface_retention_depth_is_rejected():
    with pytest.raises(ValueError, match="surface_retention_depth_m"):
        numerics(surface_retention_depth_m=-1.0e-3)


def test_result_echoes_inputs_and_software_versions():
    result = run_dynamic_pool(
        DynamicPoolConfig(zero_heat_surface(), numerics()),
        DeclaredInflow((0.0,), (0.0,)),
        (0.0, 0.1),
    )
    assert result.configuration_echo is not None
    assert result.configuration_echo["surface_type"] == "SolidSemiInfiniteSurface"
    assert result.configuration_echo["numerics"]["radial_step_m"] == 0.025
    assert result.software_versions is not None
    assert {"python", "numpy", "coolprop"} <= result.software_versions.keys()
