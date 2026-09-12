from dynamiclh2poolx import (
    ConstantHeatFluxWaterSurface,
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    run_dynamic_pool,
)


def run_with_closure(closure: str):
    return run_dynamic_pool(
        DynamicPoolConfig(
            ConstantHeatFluxWaterSurface(8.0e4, "closure test"),
            ShallowLayerNumerics(
                domain_radius_m=0.8,
                radial_step_m=0.02,
                maximum_time_step_s=0.01,
                source_radius_m=0.10,
                reported_front_depth_m=1.0e-5,
            ),
            evaporation_momentum_closure=closure,  # type: ignore[arg-type]
        ),
        DeclaredInflow((0.0, 0.5), (0.2, 0.0)),
        (0.0, 0.5, 1.0),
    )


def test_default_closure_is_fixed_before_validation():
    result = run_with_closure("zero_radial_momentum_vapor")
    assert all(
        row.evaporation_momentum_closure == "zero_radial_momentum_vapor"
        for row in result.ledger
    )


def test_alternative_closure_is_a_distinct_structural_sensitivity():
    zero_vapor_momentum = run_with_closure("zero_radial_momentum_vapor")
    liquid_carryoff = run_with_closure("liquid_velocity_carryoff")
    zero_final = zero_vapor_momentum.ledger[-1]
    carryoff_final = liquid_carryoff.ledger[-1]
    assert carryoff_final.evaporation_momentum_closure == "liquid_velocity_carryoff"
    assert (
        zero_final.radius_m != carryoff_final.radius_m
        or zero_final.liquid_mass_kg != carryoff_final.liquid_mass_kg
    )
