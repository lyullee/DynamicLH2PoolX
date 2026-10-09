# Frozen post-shutoff pool study 2026-10-09

This archive supports the Korean manuscript evaluating liquid inventory and
evaporation after liquid-hydrogen inflow shutoff. It contains original snapshots
LH2PoolX 0.1.2 and DynamicLH2PoolX 0.2.0.dev0; newer releases change only packaging,
documentation and study material. Recorded source hashes identify the calculation.

## Reproduce

From this directory, in Python 3.12:

```
python -m pip install -r requirements.txt
python code/verify_saved_evidence.py
python code/run_kci_calculations.py
python code/plot_kci_figures.py
```

The calculation script reuses existing scenario JSON only when its configuration
matches; JUEL runs are recalculated. To force a fresh scenario, move the corresponding
results JSON out of this directory before running. Tests can be run separately:

```
python -m pytest model_snapshot/dynamiclh2poolx/tests -q
python -m pytest model_snapshot/lh2poolx/tests -q
```

Set PYTHONPATH to the corresponding snapshot src directory for each test invocation.
`code/time_kci_pool.py` repeats the baseline calculation; the original machine's
14.713 s median is not portable hardware performance.
HSE regeneration uses the snapshot runner and requires independently obtained
RR985/RR986 PDFs; the command is printed in `code/reproduce_hse.py`. Copyrighted
source reports and unpublished institution records are not included.

## Evidence roles

JUEL and HSE observation CSVs are published-figure transcriptions with provenance,
not raw experimental telemetry. Water Trial 3 and aluminium Trial 5 calibrate
surface parameters; Trials 4 and 6 assess those frozen parameters. The HSE complete
trajectory RMSE is 0.438 m despite matching the reported endpoint window.
Scenario CSVs and JSON ledgers are model predictions, not new measurements.
No atmospheric concentration or safe re-entry time is computed.

Code is covered by the parent MIT license. Study-generated scenario results are
released under CC BY 4.0. Third-party observation transcriptions retain the original
report attribution and rights; no claim of ownership of the underlying experiments
is made. Sources: Dienhart JUEL-3155 (1995), https://juser.fz-juelich.de/record/860517;
HSE RR985 and RR986 (2014), https://www.hse.gov.uk/research/rrpdf/rr985.pdf and
https://www.hse.gov.uk/research/rrpdf/rr986.pdf.
