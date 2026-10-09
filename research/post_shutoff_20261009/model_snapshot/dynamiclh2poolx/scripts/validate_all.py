"""Reproduce the numerical, fixed-area, and spreading validation record."""
from pathlib import Path
import argparse
import subprocess
import sys
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset-dir',type=Path,required=True)
    p.add_argument('--xie-pdf',type=Path,required=True)
    p.add_argument('--dienhart-pdf',type=Path,required=True)
    a=p.parse_args()
    (ROOT/'outputs').mkdir(exist_ok=True)
    subprocess.run([sys.executable,'-m','pytest','-q','--junitxml=outputs/numerical_tests.xml'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/run_dynamic_validation.py','--dataset-dir',str(a.dataset_dir.resolve())],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/run_validation_xie2023.py','--pdf',str(a.xie_pdf.resolve())],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/run_validation_spreading.py','--report-pdf',str(a.dienhart_pdf.resolve())],cwd=ROOT,check=True)
    preslhy=json.loads((ROOT/'outputs/dynamic_validation/summary.json').read_text())
    xie=json.loads((ROOT/'outputs/xie2023/manifest.json').read_text())
    spreading=json.loads((ROOT/'outputs/spreading_validation/manifest.json').read_text())
    stage_c_path=ROOT/'outputs/stage_c/manifest.json'
    stage_c=json.loads(stage_c_path.read_text()) if stage_c_path.exists() else None
    passed=(
        xie['decision']=='PASS_FIXED_AREA_PTC_RATE_REPRODUCTION'
        and spreading['decision']=='PASS_RESTRICTED_SPREADING'
        and stage_c is not None
        and stage_c['decision']=='PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE'
    )
    summary={
        'decision':'PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE' if passed else 'INCOMPLETE_COMPONENT_VALIDATION',
        'numerical_tests':'PASS',
        'fixed_area_rate_validation':xie['decision'],
        'spreading_validation':spreading['decision'],
        'stage_c_reinforcement':stage_c['decision'] if stage_c else 'NOT_RUN',
        'preslhy_stress_diagnostic':preslhy['decision'],
        'scope':'Declared liquid inflow on level water or homogeneous solid surfaces; smooth axisymmetric shallow-layer pool.',
    }
    (ROOT/'outputs/validation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return 0 if passed else 2


if __name__=='__main__': raise SystemExit(main())
