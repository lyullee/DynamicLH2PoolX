"""Analytical limiting cases and cross-step conservation of the actual solver."""
from dataclasses import replace
import json
import pytest
from dynamiclh2poolx import DeclaredInflow, FixedAreaPoolConfig, run_fixed_area_pool, Substrate


@pytest.mark.parametrize('mass',[0.,.001,10.])
@pytest.mark.parametrize('heat_cap',[1.,120000.,1e12,None])
def test_mass_conservation_at_every_sample(mass,heat_cap):
    c=FixedAreaPoolConfig(area_m2=.25,initial_liquid_mass_kg=mass,critical_heat_flux_W_m2=heat_cap)
    result=run_fixed_area_pool(c,DeclaredInflow((0.,3.7,12.1),(0.,.1,0.)),(0.,1.,5.,10.,20.,50.))
    for r in result.ledger:
        assert r.liquid_mass_kg+r.cumulative_evaporation_kg==pytest.approx(mass+r.cumulative_inflow_kg,abs=1e-10)
        assert min(r.liquid_mass_kg,r.mean_depth_m,r.evaporation_rate_kg_s)>=0
    assert result.from_dict(json.loads(json.dumps(result.to_dict(),allow_nan=False)))==result


def test_higher_conductivity_and_temperature_do_not_retain_more_liquid():
    base=FixedAreaPoolConfig(area_m2=.1,initial_liquid_mass_kg=10)
    inflow=DeclaredInflow((0.,),(.01,))
    configs=[base,replace(base,substrate=Substrate('higher_k',4,2.5e-7)),replace(base,ambient_temperature_K=320)]
    results=[run_fixed_area_pool(c,inflow,(0.,10.,50.)) for c in configs]
    assert all(r.ledger[-1].liquid_mass_kg<=results[0].ledger[-1].liquid_mass_kg for r in results[1:])


def test_zero_flux_no_inflow_retains_inventory():
    r=run_fixed_area_pool(FixedAreaPoolConfig(area_m2=1,initial_liquid_mass_kg=2,ambient_temperature_K=20),DeclaredInflow((0.,),(0.,)),(0.,1.,100.))
    assert all(x.liquid_mass_kg==2 for x in r.ledger)
    assert not r.disappearance_times_s


def test_thermal_age_is_not_reset_on_postfill_start():
    from dynamiclh2poolx.conduction import ConductionCapacity
    c=ConductionCapacity(2,float('inf'))
    assert c.integral(100,400)==pytest.approx(40.)
    assert c.integral(100,400)<c.integral(0,300)
