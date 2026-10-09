"""Publication plots from recorded CSV/JSON; never refits or alters model outputs."""
from pathlib import Path
import csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Arial','font.size':10,'axes.labelsize':10,'axes.titlesize':10.5,'legend.fontsize':9,'xtick.labelsize':9,'ytick.labelsize':9,'axes.linewidth':.8,'lines.linewidth':1.5,'savefig.dpi':300,'svg.fonttype':'none','axes.unicode_minus':False})
BLUE='#0072B2';ORANGE='#D55E00';GREEN='#009E73';GRAY='#777777';INK='#222222'
captions={}

def csvrows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def values(rows,key):return np.array([float(r[key]) for r in rows])
def clean(ax):
    ax.spines[['top','right']].set_visible(False);ax.tick_params(direction='out',length=3);ax.grid(alpha=.15,linewidth=.6);ax.set_axisbelow(True)
def panel(ax,tag,title):ax.set_title(f'({tag}) {title}',loc='left',pad=10,fontweight='bold');clean(ax)
def save(fig,name,caption):
    for ext in ['png','svg','tif']:
        kwargs={'pil_kwargs':{'compression':'tiff_lzw'}} if ext=='tif' else {}
        fig.savefig(FIG/f'{name}.{ext}',facecolor='white',dpi=300,**kwargs)
    captions[name]=caption;plt.close(fig)

def figure1():
    f,ax=plt.subplots(figsize=(8.4,3.25));ax.set(xlim=(0,12),ylim=(0,4));ax.axis('off')
    def box(x,y,w,h,txt,color):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.08,rounding_size=0.08',facecolor=color,edgecolor=GRAY,lw=.8))
        ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=10.0)
    def arrow(a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,lw=1.2,color=INK))
    box(.2,2.15,2.2,1.05,'Release conditions\nPressure / liquid state','#E9ECEF')
    box(3.05,2.15,2.65,1.05,'Flash calculation\nDeclared liquid\nreaching surface','#E8F2F8')
    box(6.4,2.15,2.25,1.05,'Quasi-steady source\nHeat-limited balance\nLH2PoolX','#F4EFE5')
    box(9.3,2.15,2.35,1.05,'Instantaneous balance\nNo stored liquid','#F4EFE5')
    box(6.4,.55,2.25,1.05,'Dynamic pool\nDynamicLH2PoolX','#E7F3EE')
    box(9.3,.55,2.35,1.05,'Liquid inventory\nTime-dependent\nevaporation','#E7F3EE')
    box(3.05,.55,2.65,1.05,'Surface heat transfer\nSpreading + mass balance','#E7F3EE')
    arrow((2.5,2.67),(2.95,2.67));arrow((5.8,2.67),(6.3,2.67));arrow((8.75,2.67),(9.2,2.67))
    arrow((5.7,2.15),(6.6,1.6));arrow((5.8,1.08),(6.3,1.08));arrow((8.75,1.08),(9.2,1.08))
    ax.text(4.35,3.6,'Both branches receive the same declared ground inflow',ha='center',fontsize=10.0,fontweight='bold')
    ax.text(6,.05,'This comparison starts after liquid has reached the surface.',ha='center',color=GRAY,fontsize=9.5)
    f.subplots_adjust(left=.02,right=.99,top=.97,bottom=.03)
    save(f,'Fig1_model_workflow','Model workflow. The comparison starts with the same declared ground-reaching liquid input. Flashing is an upstream bookkeeping operation; ground deposition is not predicted. LH2PoolX gives a quasi-steady source, whereas DynamicLH2PoolX stores and evaporates liquid inventory. No atmospheric dispersion calculation is performed.')

def figure2():
    comp=csvrows(ROOT/'data/juel_radius_comparison.csv');trace=csvrows(ROOT/'data/juel_trajectories.csv');metrics=csvrows(ROOT/'data/juel_metrics.csv')
    f,axs=plt.subplots(2,2,figsize=(8.2,5.8),sharex=True,sharey=True)
    for ax,(surface,role,trial,tag) in zip(axs.flat,[('water','calibration',3,'a'),('water','holdout',4,'b'),('aluminium','calibration',5,'c'),('aluminium','holdout',6,'d')]):
        rows=[r for r in comp if r['surface']==surface and r['role']==role and float(r['time_s'])<=62]
        tr=[r for r in trace if r['surface']==surface and float(r['time_s'])<=62]
        obs=values(rows,'observed_radius_m')
        ax.errorbar(values(rows,'time_s'),obs,xerr=values(rows,'time_bound_s'),yerr=[obs-values(rows,'radius_lower_bound_m'),values(rows,'radius_upper_bound_m')-obs],fmt='o',color=INK,ecolor='#AAAAAA',ms=4,capsize=2,elinewidth=.8,label='Reported points + digitisation bounds')
        ax.plot(values(tr,'time_s'),values(tr,'reported_radius_m'),color=BLUE,label='Dynamic model')
        band=(.4,.6) if surface=='water' else (.3,.5)
        ax.fill_between([10,60],band[0],band[1],color=GRAY,alpha=.10,label='Reported video band (10-60 s)')
        m=next(m for m in metrics if m['surface']==surface and m['role']==role)
        ax.text(.97,.95,f"RMSE {float(m['rmse_m']):.3f} m\nn = {int(m['n'])}",transform=ax.transAxes,ha='right',va='top',fontsize=9.0,color=GRAY)
        panel(ax,tag,f'{surface.capitalize()}: Trial {trial} ({role})');ax.set(xlim=(-1,66),ylim=(0,1.05))
    for ax in axs[1]:ax.set_xlabel('Time from inflow start (s)')
    for ax in axs[:,0]:ax.set_ylabel('Reported pool radius (m)')
    h,l=axs[0,0].get_legend_handles_labels();f.legend(h,l,loc='upper center',bbox_to_anchor=(.5,1.0),ncol=2,frameon=False)
    f.subplots_adjust(left=.09,right=.99,top=.84,bottom=.10,hspace=.33,wspace=.16)
    save(f,'Fig2_JUEL_radius_validation','JUEL-3155 radius comparison. Trial 3 (water) and Trial 5 (aluminium) supplied the frozen surface parameters; Trials 4 and 6 assess those settings. Observations are archived figure transcriptions, with digitisation bounds rather than statistical confidence intervals. The shaded video band describes a separate reported observation. All metrics use the stated points at times up to 62 s. The water closure applies to this short regime.')

def figure3():
    comp=csvrows(ROOT/'results/hse_validation/radius_comparison.csv');tr=csvrows(ROOT/'results/hse_validation/trajectory.csv')
    manifest=json.loads((ROOT/'results/hse_validation/manifest.json').read_text())
    f,axs=plt.subplots(1,2,figsize=(8.2,3.75))
    a,b=axs
    release=[r for r in comp if r['phase']=='release'];post=[r for r in comp if r['phase']=='post_release']
    a.errorbar(values(release,'time_s'),values(release,'observed_radius_m'),xerr=values(release,'time_bound_s'),yerr=values(release,'radius_bound_m'),fmt='o',ms=4,color=INK,ecolor='#AAAAAA',capsize=2,label='Reported points + digitisation bounds')
    a.plot(values(tr,'time_s'),values(tr,'reported_radius_m'),color=BLUE,label='Dynamic model');a.axvline(561,color=GRAY,ls='--',lw=1)
    a.set(xlim=(0,620),ylim=(0,1.55),xlabel='Time from inflow start (s)',ylabel='Reported pool radius (m)')
    a.text(.05,.10,f"Release-trajectory RMSE\n{manifest['trajectory_metrics_diagnostic_only']['point_rmse_m']:.3f} m",transform=a.transAxes,ha='left',va='bottom',fontsize=9.0,color=GRAY)
    a.annotate('Observed expansion / retraction',xy=(218,1.3),xytext=(310,1.46),fontsize=8.5,arrowprops={'arrowstyle':'-','lw':.7,'color':GRAY},ha='center')
    posttr=[r for r in tr if float(r['time_s'])>=561]
    b.errorbar(values(post,'time_s')-561,values(post,'observed_radius_m'),xerr=values(post,'time_bound_s'),yerr=values(post,'radius_bound_m'),fmt='o',ms=4,color=INK,ecolor='#AAAAAA',capsize=2)
    b.plot(values(posttr,'time_s')-561,values(posttr,'reported_radius_m'),color=BLUE)
    b.axvspan(12,22,color=GRAY,alpha=.12,label='Reported dryout window')
    dry=manifest['primary_result']['reported_dryout_after_release_stop_s'];b.axvline(dry,color=GREEN,ls='--',lw=1,label=f'Model reported dryout: {dry:g} s')
    b.set(xlim=(0,60),ylim=(0,1.55),xlabel='Time after inflow stops (s)');panel(a,'a','During release');panel(b,'b','After shutoff')
    h,l=a.get_legend_handles_labels();h2,l2=b.get_legend_handles_labels();f.legend(h+h2,l+l2,ncol=2,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.01))
    f.subplots_adjust(left=.09,right=.99,top=.77,bottom=.16,wspace=.20)
    save(f,'Fig3_HSE_radius_and_dryout','HSE RR985/RR986 Test 6, using archived radius transcriptions and same-case thermal inputs. Full release trajectory differences are retained; the smooth model misses the expansion/retraction associated in RR985 with condensed-air deposition. The model front disappears at the stated depth threshold, compared with the reported thermocouple-defined dryout window. This is not a direct measurement of liquid inventory exhaustion or atmospheric safety.')

def figure4():
    rows=csvrows(ROOT/'data/matched_source_comparison.csv');t=values(rows,'time_s');q=values(rows,'dynamic_interval_mean_kg_s');qi=values(rows,'ground_inflow_interval_mean_kg_s');m=values(rows,'liquid_inventory_kg');cut=np.flatnonzero(t==561)[0]
    summary=next(r for r in csvrows(ROOT/'data/scenario_summary.csv') if float(r['rate_kg_s'])==.0707 and float(r['shutoff_s'])==561)
    f,axs=plt.subplots(2,2,figsize=(8.8,6.1));a,b,c,d=axs.flat
    a.stairs(q[1:],t,baseline=None,color=BLUE,label='Dynamic evaporation (interval mean)');a.stairs(qi[1:],t,baseline=None,color=ORANGE,ls='--',label='Quasi-steady balance / ground inflow');a.axvline(561,color=GRAY,ls=':',lw=1)
    a.set(xlim=(0,650),xlabel='Time from inflow start (s)',ylabel='Mass rate (kg/s)');panel(a,'a','Matched source histories')
    mask=t>=561;rel=t[mask]-561
    b.stairs(q[mask][1:],rel,baseline=None,color=BLUE);b.axhline(0,color=ORANGE,ls='--',lw=1.3)
    b.set(xlim=(0,90),xlabel='Time after inflow stops (s)',ylabel='Mass rate (kg/s)');panel(b,'b','Post-shutoff evaporation')
    c.plot(t,m,color=BLUE);c.axvline(561,color=GRAY,ls=':',lw=1)
    c.set(xlim=(0,650),xlabel='Time from inflow start (s)',ylabel='Liquid inventory (kg)');panel(c,'c','Stored liquid before\nand after shutoff')
    c.text(.04,.95,f"At shutoff: {m[cut]:.3f} kg",transform=c.transAxes,ha='left',va='top',fontsize=9.0)
    postevap=values(rows,'dynamic_cumulative_evaporation_kg')[mask]-values(rows,'dynamic_cumulative_evaporation_kg')[cut]
    d.plot(rel,100*postevap/m[cut],color=BLUE)
    for pct,key,color in [(90,'t90_after_stop_s',GREEN),(99,'t99_after_stop_s',GRAY)]:
        tt=float(summary[key]);d.plot(tt,pct,'o',ms=4,color=color);d.annotate(f'{pct}% at {tt:.1f} s',xy=(tt,pct),xytext=((30,74) if pct==90 else (43,52)),fontsize=8.5,color=color,arrowprops={'arrowstyle':'-','lw':.6,'color':color,**({'connectionstyle':'angle,angleA=0,angleB=-90,rad=0'} if pct==99 else {})})
    d.set(xlim=(0,90),ylim=(0,105),xlabel='Time after inflow stops (s)',ylabel='Post-shutoff evaporated\nfraction (%)');panel(d,'d','Evaporation of the\nshutoff inventory')
    h,l=a.get_legend_handles_labels();f.legend(h,l,ncol=1,loc='upper center',bbox_to_anchor=(.5,1.0),frameon=False)
    f.subplots_adjust(left=.10,right=.99,top=.84,bottom=.10,hspace=.53,wspace=.31)
    save(f,'Fig4_matched_sources_and_inventory','Matched-source comparison for declared ground inflow 0.0707 kg/s, shutoff at 561 s, concrete at 266 K. Both branches use the same hydrogen and substrate properties without a heat-flux cap. Quasi-steady evaporation equals input by construction; its post-shutoff zero is a memoryless comparator, not a validated post-shutoff LH2PoolX prediction. Rates are interval means from cumulative mass differences. The dynamic model stores inventory and continues to evaporate it. The 90% and 99% times concern predicted liquid inventory, not measured vapour rates or safe re-entry.')

def figure5():
    rows=csvrows(ROOT/'data/scenario_summary.csv');rates=sorted({float(r['rate_kg_s']) for r in rows})
    f,axs=plt.subplots(1,3,figsize=(10.8,4.1))
    for rate,color,marker in zip(rates,[BLUE,GREEN,ORANGE],['o','s','^']):
        r=sorted([r for r in rows if float(r['rate_kg_s'])==rate],key=lambda x:float(x['shutoff_s']))
        for ax,key,factor in zip(axs,['inventory_at_stop_kg','t99_after_stop_s','inventory_fraction_at_stop'],[1,1,100]):
            ax.plot(values(r,'shutoff_s'),values(r,key)*factor,marker=marker,ms=5,color=color,label=f'{rate:.5f} kg/s')
    for ax,tag,title,ylabel in zip(axs,'abc',['Residual liquid','Post-shutoff\nevaporation time','Residual share of input'],['Liquid inventory at shutoff (kg)','Time to evaporate 99%\nof residual (s)','Inventory / cumulative\nground inflow (%)']):
        panel(ax,tag,title);ax.set(xlim=(40,580),xlabel='Shutoff time (s)',ylabel=ylabel);ax.set_xticks([60,180,561]);ax.set_ylim(bottom=0)
    h,l=axs[0].get_legend_handles_labels();f.legend(h,l,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.0),frameon=False,title='Declared ground-reaching liquid rate')
    f.subplots_adjust(left=.065,right=.985,top=.75,bottom=.17,wspace=.37)
    save(f,'Fig5_shutoff_scenario_comparison','Nine conditional concrete scenarios with ground-reaching liquid rates 0.03535, 0.07070 and 0.14140 kg/s and shutoff times 60, 180 and 561 s. Curves connect the three computed scenarios per rate to aid reading; they are not fitted laws. Surface/source/retention settings are unchanged. Outputs are model predictions, not additional experiments. The 99% time refers to the inventory at shutoff; no concentration or danger-zone duration is calculated.')

def supplement():
    rows=csvrows(ROOT/'data/sensitivity_summary.csv');base=next(r for r in csvrows(ROOT/'data/scenario_summary.csv') if float(r['rate_kg_s'])==.0707 and float(r['shutoff_s'])==561)
    f,axs=plt.subplots(1,2,figsize=(8.1,4.1),sharey=True)
    labels={'T0_256K':'Initial surface: 256 K','T0_276K':'Initial surface: 276 K','k_0.744':'Conductivity: -20%','k_1.116':'Conductivity: +20%','front_0.5mm':'Reported front: 0.5 mm','front_1.0mm':'Reported front: 1.0 mm','fine_dr_dt':'Refined space / time'}
    y=np.arange(len(rows))
    for ax,key,title,xlabel,tag in zip(axs,['inventory_at_stop_kg','t99_after_stop_s'],['Inventory sensitivity','Evaporation-time sensitivity'],['Inventory at shutoff (kg)','Time to evaporate 99% (s)'],'ab'):
        ax.plot(values(rows,key),y,'o',color=BLUE,ms=5);ax.axvline(float(base[key]),color=GRAY,ls='--',lw=1,label='Frozen base');ax.set_yticks(y,[labels[r['case']] for r in rows]);ax.set_xlabel(xlabel);panel(ax,tag,title)
    axs[0].invert_yaxis();axs[1].legend(frameon=False,loc='lower right')
    f.subplots_adjust(left=.25,right=.98,top=.85,bottom=.16,wspace=.23)
    save(f,'FigS1_parameter_and_resolution_sensitivity','One-at-a-time sensitivity at 0.0707 kg/s and 561 s. Temperature, conductivity and numerical/front settings are varied around the frozen baseline, not fitted to improve observations. The reporting-depth threshold affects the observed front and does not remove hidden liquid inventory. These ranges are sensitivity checks, not confidence intervals.')

def numerical_rates():
    coarse=json.loads((ROOT/'results/scenario_q0.07070_stop561.json').read_text())['result']['ledger']
    fine=json.loads((ROOT/'results/fine_dr_dt.json').read_text())['result']['ledger']
    t=np.array([r['time_s'] for r in coarse]);qc=np.array([r['interval_mean_evaporation_rate_kg_s'] for r in coarse]);qf=np.array([r['interval_mean_evaporation_rate_kg_s'] for r in fine])
    f,axs=plt.subplots(1,2,figsize=(8,3.5))
    for ax,tag,title,limits in zip(axs,'ab',['During inflow','After shutoff'],[(300,340),(561,586)]):
        mask=(t>=limits[0])&(t<=limits[1]);tt=t[mask]
        origin=0 if tag=='a' else 561
        ax.stairs(qc[mask][1:],tt-origin,baseline=None,color=BLUE,label='dr = 0.010 m; dt <= 0.020 s')
        ax.stairs(qf[mask][1:],tt-origin,baseline=None,color=ORANGE,label='dr = 0.005 m; dt <= 0.010 s')
        panel(ax,tag,title);ax.set_xlabel('Time from inflow start (s)' if tag=='a' else 'Time after inflow stops (s)');ax.set_ylabel('Evaporation rate: 1 s mean (kg/s)')
    h,l=axs[0].get_legend_handles_labels();f.legend(h,l,ncol=1,loc='upper center',bbox_to_anchor=(.5,1.01),frameon=False)
    f.subplots_adjust(left=.095,right=.99,top=.78,bottom=.17,wspace=.28)
    save(f,'FigS2_rate_resolution_check','Raw 1 s interval evaporation rates from the two space/time resolutions. Short-period rate structure changes with cell resolution and is not interpreted as observed physical pulsation. Shutoff inventory changes by approximately 1.6% and the model 99% time changes by less than 0.1 s. Main conclusions concern inventory, integrated mass and post-shutoff timing, rather than unvalidated instantaneous rate detail.')

def main():
    figure1();figure2();figure3();figure4();figure5();supplement();numerical_rates()
    (FIG/'figure_captions.json').write_text(json.dumps(captions,indent=2),encoding='utf-8')
    (FIG/'FIGURE_CAPTIONS.txt').write_text('\n\n'.join(f'{k}\n{v}' for k,v in captions.items()),encoding='utf-8')
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(1600,1960),'white');d=ImageDraw.Draw(sheet)
    for i,p in enumerate(sorted(FIG.glob('Fig*.png'))):
        im=Image.open(p).convert('RGB');im.thumbnail((775,435));x=(i%2)*800+(800-im.width)//2;y=(i//2)*490+30
        sheet.paste(im,(x,y));d.text(((i%2)*800+10,(i//2)*490+8),p.stem,fill='black')
    sheet.save(FIG/'all_figures_preview.png')
    print('Figures exported: PNG, SVG, TIFF; no model rerun',flush=True)

if __name__=='__main__':main()
