from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]
if len(sys.argv)!=3:raise SystemExit('Usage: python code/reproduce_hse.py /path/RR985.pdf /path/RR986.pdf')
subprocess.run([sys.executable,str(root/'model_snapshot/dynamiclh2poolx/scripts/run_validation_hse_test6.py'),'--rr985-pdf',sys.argv[1],'--rr986-pdf',sys.argv[2],'--output-dir',str(root/'results/hse_validation')],check=True)
