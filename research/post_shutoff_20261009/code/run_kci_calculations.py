"""Frozen ground-inflow pool study; run with the project's .venv-transfer Python."""
from __future__ import annotations
from dataclasses import asdict, replace
from pathlib import Path
import csv, hashlib, json, platform, sys, time
import numpy as np

OUT = Path(__file__).resolve().parents[1]
MODEL = OUT / 'model_snapshot/dynamiclh2poolx'
STATIC = OUT / 'model_snapshot/lh2poolx'
sys.path[:0] = [str(MODEL/'src'), str(MODEL/'scripts'), str(STATIC/'src')]
from dynamiclh2poolx import DeclaredInflow, DynamicPoolConfig, ShallowLayerNumerics, SolidSemiInfiniteSurface, run_dynamic_pool
from lh2poolx.pool import LH2Release, Substrate, evaluate_pool_source
from run_validation_spreading import _run as juel_run, read_observations
from dynamiclh2poolx import ConstantHeatFluxWaterSurface

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def write_json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def juel_validation():
    """Replay archived digitised observations; no new source-PDF transcription."""
    obs=read_observations(); rows=[];summaries=[]; trajectories=[];sensitivity=[]
    for surface in ['water','aluminium']:
        base=200000. if surface=='water' else .40
        vals=[180000.,200000.,220000.] if surface=='water' else [.35,.40,.45]
        for value in vals:
            cfg=(ConstantHeatFluxWaterSurface(value,'frozen JUEL Trial 3 calibration') if surface=='water' else
                 SolidSemiInfiniteSurface('JUEL aluminium',204.,204./(2700.*879.),277.9,heat_flux_multiplier=value))
            result=juel_run(cfg,.005 if surface=='water' else .006,98600.)
            selected=[o for o in obs if o['surface']==surface and o['role']=='holdout' and o['time_s']<=62]
            err=np.array([result.ledger[int(o['time_s'])].reported_radius_m-o['observed_radius_m'] for o in selected])
            sensitivity.append(dict(surface=surface,parameter=value,holdout_rmse_m=float(np.sqrt(np.mean(err**2))),radius_at_60s_m=result.ledger[60].reported_radius_m,is_frozen_base=value==base))
            if value!=base:continue
            trajectories += [dict(surface=surface,**asdict(l)) for l in result.ledger]
            for o in [o for o in obs if o['surface']==surface]:
                pred=result.ledger[int(o['time_s'])].reported_radius_m
                rows.append(dict(**o,predicted_radius_m=pred,residual_m=pred-o['observed_radius_m']))
            for role in ['calibration','holdout']:
                sel=[o for o in rows if o['surface']==surface and o['role']==role and o['time_s']<=62]
                e=np.array([o['residual_m'] for o in sel])
                summaries.append(dict(surface=surface,role=role,n=len(sel),rmse_m=float(np.sqrt(np.mean(e**2))),mae_m=float(np.mean(abs(e))),bias_m=float(np.mean(e)),mass_balance_residual_kg=result.mass_balance_residual_kg))
    write_csv(OUT/'data/juel_radius_comparison.csv',rows)
    write_csv(OUT/'data/juel_trajectories.csv',trajectories)
    write_csv(OUT/'data/juel_metrics.csv',summaries)
    write_csv(OUT/'data/juel_parameter_sensitivity.csv',sensitivity)
    write_json(OUT/'results/juel_replay_manifest.json',dict(metrics=summaries,source='archived figure transcription; original report website returned a challenge page, not a PDF',observation_sha256=hashlib.sha256((MODEL/'data/juel3155_radius_observations.csv').read_bytes()).hexdigest(),parameters_reselected=False,decision='PASS_RESTRICTED_SPREADING' if all(s['rmse_m']<=.15 for s in summaries if s['role']=='holdout') else 'REQUIRES_REVIEW'))
    print('JUEL replay finished',flush=True)

def config(dr=.01,dt=.02,front=.00075,temperature=266.,k=.93,alpha=4.8e-7):
    return DynamicPoolConfig(SolidSemiInfiniteSurface('HSE-like concrete',k,alpha,temperature),
        ShallowLayerNumerics(domain_radius_m=4.,radial_step_m=dr,maximum_time_step_s=dt,
         chezy_coefficient=1e-3,source_radius_m=.025,surface_retention_depth_m=.005,
         dry_depth_m=1e-8,reported_front_depth_m=front),evaporation_momentum_closure='zero_radial_momentum_vapor')

def sample_times(stop,tail=180,step=1.):
    return tuple(sorted(set([0.,float(stop),float(stop+tail)]+list(np.arange(0,stop+tail+.00001,step)))))

def summarise(result,stop,rate,runtime,label):
    rows=result.ledger;cut=next(l for l in rows if l.time_s==stop);tail=[l for l in rows if l.time_s>=stop]
    cumulative=np.array([l.cumulative_evaporation_kg-cut.cumulative_evaporation_kg for l in tail]);ts=np.array([l.time_s-stop for l in tail])
    def quantile(frac):
        target=cut.liquid_mass_kg*frac
        return float(np.interp(target,cumulative,ts)) if cumulative[-1]>=target and target>0 else None
    dry=next((l.time_s-stop for l in tail if l.time_s>stop and l.reported_radius_m==0),None)
    exhaust=next((l.time_s-stop for l in tail if l.time_s>stop and l.liquid_mass_kg<=1e-12),None)
    return dict(case=label,rate_kg_s=rate,shutoff_s=stop,total_inflow_kg=rate*stop,
     inventory_at_stop_kg=cut.liquid_mass_kg,inventory_fraction_at_stop=cut.liquid_mass_kg/(rate*stop),
     post_stop_evaporation_kg=float(cumulative[-1]),remaining_at_end_kg=rows[-1].liquid_mass_kg,
     t90_after_stop_s=quantile(.90),t99_after_stop_s=quantile(.99),reported_dryout_after_stop_s=dry,
     inventory_exhaustion_after_stop_s=exhaust,end_of_release_radius_m=cut.reported_radius_m,
     max_unledgered_residual_kg=max(abs(l.unledgered_mass_residual_kg) for l in rows),
     numerical_adjustment_kg=rows[-1].cumulative_numerical_mass_adjustment_kg,
     escaped_mass_kg=rows[-1].escaped_domain_mass_kg,solver_wall_time_s=runtime)

def run_case(rate,stop,cfg,label,step=1.):
    cache=OUT/'results'/f'{label}.json'
    if cache.exists():
        from dynamiclh2poolx import DynamicPoolResult
        payload=json.loads(cache.read_text(encoding='utf-8'))
        desired={'surface_type':type(cfg.surface).__name__,'surface':asdict(cfg.surface),'numerics':asdict(cfg.numerics),
          'ambient_pressure_Pa':cfg.ambient_pressure_Pa,'initial_liquid_mass_kg':cfg.initial_liquid_mass_kg,
          'evaporation_momentum_closure':cfg.evaporation_momentum_closure,
          'inflow':asdict(DeclaredInflow((0.,float(stop)),(rate,0.))),
          'output_times_s':list(sample_times(stop,step=step))}
        desired=json.loads(json.dumps(desired))
        if payload['result']['configuration_echo']!=desired:
            raise ValueError(f'Cached configuration differs for {label}; use a fresh result label or folder.')
        return DynamicPoolResult.from_dict(payload['result']),payload['runtime_s']
    tick=time.perf_counter()
    result=run_dynamic_pool(cfg,DeclaredInflow((0.,float(stop)),(rate,0.)),sample_times(stop,step=step))
    elapsed=time.perf_counter()-tick
    write_json(cache,dict(result=result.to_dict(),runtime_s=elapsed))
    print(f'{label}: {elapsed:.2f}s, residual={result.mass_balance_residual_kg:.3g}kg',flush=True)
    return result,elapsed

def main():
    juel_validation()
    protocol=json.loads((OUT/'code/protocol.json').read_text(encoding='utf-8'));summary=[];traces=[]
    for rate in protocol['rate_kg_s']:
        for stop in protocol['shutoff_s']:
            label=f'scenario_q{rate:.5f}_stop{stop}'
            result,elapsed=run_case(rate,stop,config(),label)
            summary.append(summarise(result,stop,rate,elapsed,label))
            for l in result.ledger:
                traces.append(dict(case=label,rate_kg_s=rate,shutoff_s=stop,**asdict(l)))
            write_csv(OUT/'data/scenario_summary.csv',summary)
            write_csv(OUT/'data/scenario_trajectories.csv',traces)
    # Compare steady and dynamic branches under the same declared ground inflow.
    base=json.loads((OUT/'results/scenario_q0.07070_stop561.json').read_text(encoding='utf-8'))['result']['ledger']
    release=LH2Release(.0707,0.,1.);surface=Substrate('matched HSE concrete',.93,4.8e-7);paired=[]
    for i,l in enumerate(base):
        t=l['time_s'];qs=None
        if 0<t<561:
            qs=evaluate_pool_source(release,elapsed_s=t,substrate=surface,ambient_temperature_K=266.,critical_heat_flux_W_m2=None)
            assert abs(qs.liquid_to_ground_kg_s-.0707)<1e-12
        # Rates are interval means; a 560--561 s interval precedes shutoff.
        left=base[i-1]['time_s'] if i else t
        avg_inflow=.0707*max(0.,min(t,561.)-min(left,561.))/(t-left) if i else 0.
        paired.append(dict(time_s=t,interval_start_s=left,ground_inflow_interval_mean_kg_s=avg_inflow,
          quasi_steady_interval_mean_kg_s=avg_inflow,dynamic_interval_mean_kg_s=l['interval_mean_evaporation_rate_kg_s'],
          liquid_inventory_kg=l['liquid_mass_kg'],dynamic_cumulative_evaporation_kg=l['cumulative_evaporation_kg'],
          memoryless_cumulative_evaporation_kg=.0707*min(t,561.),
          dynamic_reported_radius_m=l['reported_radius_m'],quasi_steady_radius_m=qs.radius_m if qs else None))
    write_csv(OUT/'data/matched_source_comparison.csv',paired)
    # Predeclared physical/input sensitivities and new-case numerical controls.
    sens=[];checks=[]
    for label,cfg in [('T0_256K',config(temperature=256.)),('T0_276K',config(temperature=276.)),
       ('k_0.744',config(k=.744)),('k_1.116',config(k=1.116)),
       ('front_0.5mm',config(front=.0005)),('front_1.0mm',config(front=.001)),
       ('fine_dr_dt',config(dr=.005,dt=.01))]:
        result,elapsed=run_case(.0707,561,cfg,label)
        row=summarise(result,561,.0707,elapsed,label);sens.append(row)
        write_csv(OUT/'data/sensitivity_summary.csv',sens)
    # A separate 0.5 s output grid checks rate integration and post-shutoff timing.
    result,elapsed=run_case(.0707,561,config(),'output_dt_0.5s',step=.5)
    checks.append(summarise(result,561,.0707,elapsed,'output_dt_0.5s'))
    write_csv(OUT/'data/output_resolution_check.csv',checks)
    passed=all(s['max_unledgered_residual_kg']<1e-8 and s['escaped_mass_kg']==0 and abs(s['numerical_adjustment_kg'])<1e-10 and s['t99_after_stop_s'] is not None for s in summary+sens+checks)
    write_json(OUT/'results/calculation_manifest.json',dict(protocol=protocol,software={'python':platform.python_version(),'numpy':np.__version__},scenario_count=9,sensitivity_count=7,output_resolution_count=1,scope_checks_passed=passed,source_rate_measured=False,gas_concentration_computed=False,accuracy_and_runtime_route='same snapshotted dynamic pool route; wall times are offline source-history integration, not digital-twin latency'))
    if not passed:raise RuntimeError('Scenario conservation/domain/coverage check failed')
    print('ALL CALCULATIONS COMPLETE',flush=True)

if __name__=='__main__':main()
