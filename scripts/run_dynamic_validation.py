"""Raw experimental mass trajectories, temperature checks, numerical evidence.

Run with --dataset-dir pointing at the original PRESLHY dataset directory.
No coefficient fitting. Never use the reconstructed m_lh2_g in the old rate
CSV as a measured mass. Output mass is always from original workbook cells.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import CoolProp.CoolProp as CP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from dynamiclh2poolx import DeclaredInflow, FixedAreaPoolConfig, run_fixed_area_pool


def dump_csv(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def read_raw(path):
    wb=openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        it=wb.worksheets[0].iter_rows(values_only=True)
        for _ in range(6): next(it)
        headers=[str(c).strip() if c is not None else '' for c in next(it)]
        wanted=['X_Value','Sync. Time [s]','Orig.Time [s]','m(LH2) [g]','TA000-00','TG96-00','TG91-00','TG86-00','TG46-00','TG02-00']
        idx={c:headers.index(c) for c in wanted if c in headers}
        if 'Orig.Time [s]' not in idx or 'm(LH2) [g]' not in idx:
            raise ValueError(f'Missing scale columns: {path}')
        data=[]; temperature_rows=[]
        for row in it:
            values={k:row[j] if j<len(row) else None for k,j in idx.items()}
            if isinstance(values.get('X_Value'),(int,float)):
                temperature_rows.append(values)
            if isinstance(values['Orig.Time [s]'],(int,float)) and isinstance(values['m(LH2) [g]'],(int,float)):
                data.append(values)
        # The worksheet contains TWO independent clocks side-by-side.
        # X_Value is the temperature clock; Sync.Time maps the scale onto it.
        # Never align by row index (1 s versus 0.5 s in Concrete02).
        for channel in ['TA000-00','TG96-00','TG91-00','TG86-00','TG46-00','TG02-00']:
            valid=[r for r in temperature_rows if isinstance(r.get(channel),(int,float))]
            tx=np.array([r['X_Value'] for r in valid]); vals=np.array([r[channel] for r in valid])
            for r in data:
                sync=r.get('Sync. Time [s]')
                r[channel]=float(np.interp(sync,tx,vals)) if isinstance(sync,(int,float)) and len(tx) and tx[0]<=sync<=tx[-1] else None
        return data
    finally: wb.close()


def peak_windows(t,m):
    # Source-independent fixed rule, matching previous extractor, no residual selection.
    win=max(1,round(30/(t[1]-t[0]))); i=win; peaks=[]
    while i<len(t)-win:
        if m[i]-m[i-win]>=250:
            j=i
            while j<len(t)-1 and max(m[j+1:j+1+win],default=m[j])>m[j]: j+=1
            if m[j]>=400: peaks.append((float(t[j]),float(min(t[j]+30,t[-1]))))
            i=j+win
        else: i+=1
    return peaks


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dataset-dir',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs/dynamic_validation')
    args=ap.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/'data/dynamic_validation_protocol.json').read_text())
    metrics=[]; all_rows=[]; temps=[]; sources=[]
    saturation_temperature=float(CP.PropsSI('T','P',101325,'Q',0,'Hydrogen'))
    fig,axes=plt.subplots(2,4,figsize=(15,7.5),layout='constrained')
    for ri,run in enumerate(['Concrete02','Concrete03']):
        path=next(args.dataset_dir.glob(f'*{run}*.xlsx'))
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        cache=out/f'{run}_raw_cache.json'
        cached=json.loads(cache.read_text()) if cache.exists() else {}
        raw=cached.get('rows') if cached.get('sha256')==sha and cached.get('extractor_version')==2 else None
        if raw is None:
            raw=read_raw(path); cache.write_text(json.dumps({'sha256':sha,'extractor_version':2,'rows':raw}),encoding='utf-8')
        sources.append({'path':str(path.resolve()),'sha256':sha,'sheet':0,'header_row':7,'digitised':False,'raw_rows':len(raw),'alignment':'temperature interpolated from X_Value onto scale Sync.Time; mass remains on Orig.Time'})
        t=np.array([r['Orig.Time [s]'] for r in raw]); m=np.array([r['m(LH2) [g]']/1000 for r in raw])
        windows=protocol['preslhy']['Concrete02_windows_orig_s'] if run=='Concrete02' else peak_windows(t,m*1000)
        threshold=next(float(r['Orig.Time [s]']) for r in raw if isinstance(r.get('TA000-00'),(int,float)) and r['TA000-00']<=25)
        sources[-1]['synchronised_surface_threshold_orig_s']=threshold
        origins=[500.,threshold] if run=='Concrete02' else [threshold]
        for wi,(start,end) in enumerate(windows):
            mask=(t>=start)&(t<=end); tt=t[mask]; observed=m[mask]
            if len(tt)<2 or observed[0]<=0: continue
            ax=axes[ri,wi]; ax.plot(tt-tt[0],observed,'k.',ms=2,label='Original scale samples')
            for oi,origin in enumerate(origins):
                config=FixedAreaPoolConfig(area_m2=.25,initial_liquid_mass_kg=float(observed[0]),initial_thermal_age_s=float(tt[0]-origin))
                result=run_fixed_area_pool(config,DeclaredInflow((0.,),(0.,)),tuple(float(x-tt[0]) for x in tt))
                pred=np.array([r.liquid_mass_kg for r in result.ledger]); error=pred-observed
                loss_obs=float(observed[0]-observed[-1]); loss_pred=float(observed[0]-pred[-1])
                rmse=float(np.sqrt(np.mean(error**2))); nrmse=rmse/observed[0]
                loss_error=(loss_pred-loss_obs)/loss_obs if loss_obs>0 else None
                gate=nrmse<=.3 and loss_error is not None and abs(loss_error)<=.3
                premature=bool(result.disappearance_times_s) and observed[-1] > .03
                metrics.append({'run':run,'window':wi+1,'start_orig_s':float(tt[0]),'end_orig_s':float(tt[-1]),'thermal_origin_orig_s':origin,'n_samples':len(tt),'initial_mass_kg':float(observed[0]),'rmse_kg':rmse,'mae_kg':float(np.mean(abs(error))),'bias_kg':float(np.mean(error)),'rmse_fraction_initial_mass':float(nrmse),'observed_mass_loss_kg':loss_obs,'predicted_mass_loss_kg':loss_pred,'relative_mass_loss_error':loss_error,'mass_residual_kg':result.mass_balance_residual_kg,'engineering_screen_pass':bool(gate),'premature_dryout_observed_mass_remaining':bool(premature),'disappearance_times_s':list(result.disappearance_times_s)})
                for j,row in enumerate(result.ledger):
                    all_rows.append({'run':run,'window':wi+1,'thermal_origin_orig_s':origin,'time_s':row.time_s,'observed_mass_kg':float(observed[j]),'predicted_mass_kg':row.liquid_mass_kg,'cumulative_evaporation_kg':row.cumulative_evaporation_kg,'source_rate_kg_s':row.evaporation_rate_kg_s,'radius_m':row.radius_m,'area_m2':row.area_m2,'mean_depth_m':row.mean_depth_m})
                ax.plot(tt-tt[0],pred,label=f'Conduction origin {origin:g}s')
            ax.set(title=f'{run} / window {wi+1}',xlabel='Time after window start [s]',ylabel='Liquid mass [kg]'); ax.legend(fontsize=7); ax.grid(alpha=.2)
        if len(windows)<4: axes[ri,3].axis('off')
        # Temperature is an independent observable: declared half-space erfc solution.
        for origin in origins:
            for col,depth in [('TG96-00',.004),('TG91-00',.009),('TG86-00',.014),('TG46-00',.054),('TG02-00',.098)]:
                for r in raw[::20]:
                    age=r['Orig.Time [s]']-origin; actual=r.get(col)
                    if age>0 and isinstance(actual,(int,float)) and any(a <= r['Orig.Time [s]'] <= b for a,b in windows):
                        predicted=saturation_temperature+ (282-saturation_temperature)*math.erf(depth/(2*math.sqrt(2.5e-7*age)))
                        temps.append({'run':run,'thermal_origin_orig_s':origin,'channel':col,'depth_m':depth,'thermal_age_s':age,'observed_K':actual,'predicted_K':predicted,'residual_K':predicted-actual})
    fig.suptitle('DynamicLH2PoolX: conditional PRESLHY stress diagnostic\nNo fitted coefficients; Concrete03 windows assume inflow has stopped',fontsize=13)
    fig.savefig(out/'mass_trajectories.png',dpi=180); plt.close(fig)
    dump_csv(out/'mass_metrics.csv',metrics); dump_csv(out/'mass_trajectories.csv',all_rows); dump_csv(out/'temperature_rows.csv',temps)
    tempmetrics=[]
    for key in sorted({(r['run'],r['thermal_origin_orig_s'],r['channel']) for r in temps}):
        rows=[r for r in temps if (r['run'],r['thermal_origin_orig_s'],r['channel'])==key]; err=np.array([r['residual_K'] for r in rows])
        tempmetrics.append({'run':key[0],'thermal_origin_orig_s':key[1],'channel':key[2],'n':len(rows),'rmse_K':float(np.sqrt(np.mean(err**2))),'bias_K':float(np.mean(err))})
    dump_csv(out/'temperature_metrics.csv',tempmetrics)
    f,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax,run in zip(axs,['Concrete02','Concrete03']):
        origin=500. if run=='Concrete02' else next(r['thermal_origin_orig_s'] for r in temps if r['run']==run)
        for channel in ['TG96-00','TG86-00','TG02-00']:
            points=[r for r in temps if r['run']==run and r['thermal_origin_orig_s']==origin and r['channel']==channel]
            x=[r['thermal_age_s'] for r in points]; actual=[r['observed_K'] for r in points]; pred=[r['predicted_K'] for r in points]
            line=ax.plot(x,actual,'.',label=channel+' measured')[0]
            ax.plot(x,pred,'x',color=line.get_color(),ms=3,label=channel+' predicted')
        ax.set(title=run+' / selected wet windows',xlabel='Declared thermal age [s]',ylabel='Temperature [K]'); ax.legend(fontsize=7,ncol=2)
    f.savefig(out/'temperatures.png',dpi=180); plt.close(f)
    mixed=any(not r['engineering_screen_pass'] for r in metrics if r['run']=='Concrete02' and r['thermal_origin_orig_s']==500)
    summary={'protocol':protocol,'provenance':sources,'mass_metrics':metrics,'temperature_metrics':tempmetrics,'diagnostic_status':'MIXED' if mixed else 'WITHIN_LEGACY_SCREEN','decision':'DIAGNOSTIC_MIXED_NOT_RELEASE_GATE' if mixed else 'DIAGNOSTIC_WITHIN_LEGACY_SCREEN_NOT_RELEASE_GATE','limitations':['Initial mass is observed; only subsequent samples are predictions.','Repeated fills are correlated, not independent experiments.','Concrete02 properties were inherited from this dataset.','No observed inlet record: Concrete03 windows are conditional.','Thermal threshold is not exact first wetting; 500s and threshold origins are kept separate.','Finite substrate, boiling regimes and dry-surface reheating are not represented.']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'decision':summary['decision'],'windows':metrics},indent=2))


if __name__=='__main__': main()
