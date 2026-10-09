from pathlib import Path
import csv,json,hashlib
root=Path(__file__).resolve().parents[1]
with (root/'data/scenario_summary.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
assert len(rows)==9
base=next(r for r in rows if float(r['rate_kg_s'])==.0707 and float(r['shutoff_s'])==561)
assert abs(float(base['inventory_at_stop_kg'])-1.063820624757916)<1e-10
assert abs(float(base['t99_after_stop_s'])-20.744043214)<1e-7
hashes=json.loads((root/'results/model_snapshot_sha256.json').read_text())
for rel,h in hashes.items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==h,rel
for r in rows:assert abs(float(r['max_unledgered_residual_kg']))<1e-8
print('PASS: nine scenarios, baseline metrics, immutable model source hashes and mass conservation')
