"""Repeat the same whole-history pool calculation; not a telemetry update benchmark."""
import json,platform,time,statistics
from run_kci_calculations import OUT,config,sample_times,DeclaredInflow,run_dynamic_pool,summarise,write_json
records=[]
for i in range(3):
    start=time.perf_counter()
    result=run_dynamic_pool(config(),DeclaredInflow((0.,561.),(.0707,0.)),sample_times(561))
    wall=time.perf_counter()-start
    row=summarise(result,561,.0707,wall,f'runtime_repeat_{i+1}');records.append(row)
    print(f'Repeat {i+1}: {wall:.3f} s',flush=True)
    write_json(OUT/'results/runtime_repeats.json',dict(scope='complete 741 s history from declared ground inflow, including 561 s release and 180 s tail; 1 s outputs; imports excluded; not digital-twin latency',repetitions=records,wall_time_median_s=statistics.median(r['solver_wall_time_s'] for r in records),wall_time_min_s=min(r['solver_wall_time_s'] for r in records),wall_time_max_s=max(r['solver_wall_time_s'] for r in records),workstation=dict(system=platform.platform(),processor=platform.processor(),python=platform.python_version())))
