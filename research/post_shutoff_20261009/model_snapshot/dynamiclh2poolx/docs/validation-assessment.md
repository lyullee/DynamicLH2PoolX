# DynamicLH2PoolX validation assessment

> SUPERSEDED 2026-09-11. The 1.173 component ratio below used an invalid
> temperature-to-scale clock alignment and is withdrawn. Read
> [dynamic-validation-report.md](dynamic-validation-report.md) for the corrected
> 42-test, Xie Figure 11, and Dienhart spreading validation. This file is
> retained only as an audit record and does not describe the current package.

## Verdict

DynamicLH2PoolX has a reproducible **restricted heat-transfer component check**,
but the dynamic fixed-area route is **not validated as a pool-trajectory
model**, and no spreading route exists yet.  The following evidence therefore
does not support a claim that the package predicts an LH2 impact footprint,
pool radius history, water-surface behaviour, or downstream concentration.

## Executed component comparison

The repository script `scripts/run_validation_e34_heat_transfer.py` was run
against the connected-workspace file
`C:/Users/Lyul/Desktop/SLAB 재구축/slabx-lh2/lh2_e34_rates.csv`.  The input
contains 42 derived mass-loss-rate points labelled `Concrete02`, with elapsed
time since ground cooling and observed mass flux.  The comparison used the
same solid semi-infinite-conduction and CHF-limited closure exposed by both
the quasi-steady route and the fixed-area route.

| Quantity | Result | Interpretation |
|---|---:|---|
| Observations | 42 | Concrete02 only; four fills, no crosswind |
| Median predicted / observed flux | 1.173 | modest positive central bias |
| MAE | 0.01472 kg m-2 s-1 | pointwise flux error |
| RMSE | 0.02115 kg m-2 s-1 | penalises the larger deviations |
| Bias | +0.01099 kg m-2 s-1 | model overpredicts on average |

The generated row ledger and JSON summary are written to the ignored
`outputs/e34_heat_transfer/` directory.  The command is:

```bash
python scripts/run_validation_e34_heat_transfer.py --source-csv "C:/Users/Lyul/Desktop/SLAB 재구축/slabx-lh2/lh2_e34_rates.csv"
```

This is a component comparison, not a fit: the model parameters were not
altered and no concentration result was used.  It is applicable only to the
declared concrete closure and the stated time coordinate.  The linked
PRESLHY programme identifies E3.4 as an LH2-pool experiment measuring
evaporation rate, ground material, initial temperature, and crosswind.[^1]

## Numerical-contract checks

The fixed-area implementation was exercised with the bundled Python runtime:

- constant declared inflow with zero temperature driving force: exact mass
  closure and expected final inventory;
- zero declared inflow after a finite initial inventory: no negative inventory
  and `input_limited` status after emptying;
- JSON-style `to_dict` / `from_dict` round trip: exact equality.

These are deterministic software checks, not experimental validation.  The
automated pytest suite remains included, but the ordinary system Python is
not installed in this workspace; the available bundled runtime contains
CoolProp but not pytest.

## Evidence review and scope decision

| Evidence source | Directly supports | DynamicLH2PoolX status |
|---|---|---|
| PRESLHY E3.4 Concrete02 derived mass-loss record | solid-concrete evaporation flux | compared, restricted component evidence |
| Xie et al. (2023), concrete nonspreading pool | post-fill mass loss and near-surface temperature | suitable next fixed-area benchmark; no traceable time series loaded |
| Verfondern & Dienhart (1997) | transient LH2 spreading on water and aluminium; shallow-layer model context | correct future radius/area benchmark; not used yet |
| Verfondern & Dienhart (2007) | LH2 spreading/vaporisation source-term research | corroborating literature; not a loaded validation dataset |
| HSE RR985 (2014) | model-to-experiment assessment and remaining validation needs | system-level context only; no DynamicLH2PoolX comparison |
| Middha, Ichard & Arntzen (2011) | coupled large-scale LH2 spread/evaporation CFD comparison | system-level context only; not component validation |

The Xie experiment uses a 400 mm by 400 mm concrete pad and reports that the
filling flow was not measured; its evaporation analysis begins after filling
stops.[^2]  It can therefore test the fixed-area route only over post-fill
windows, not infer its inlet history.  The 1997 Verfondern–Dienhart work
specifically reports transient tests on water and aluminium and a
shallow-layer model,[^3] which makes it an appropriate future spreading test,
not evidence for the current fixed-area solid closure.  HSE RR985 likewise
notes that heat transfer, spread, and vaporisation need separately sufficient
validation before a spill model can be treated as reliable.[^4]

## Release gate

Do not call version `0.2.0.dev0` “validated dynamic LH2 pool model.”  The
defensible current statement is:

> DynamicLH2PoolX has a tested bounded fixed-area mass-balance implementation and
> a restricted Concrete02 heat-transfer component comparison.  Its dynamic
> inventory trajectory and spreading behaviour remain unvalidated.

To lift that restriction, add a provenance-recorded post-fill Xie time series
with a calibration/validation split, reproduce mass and temperature metrics,
then implement and separately test radius/area history against the
Verfondern–Dienhart experiments.  Treat HSE/BAM/NASA only as later
system-level checks.

## Sources

[^1]: [PRESLHY, “WP3 – Release and Mixing”](https://preslhy.eu/wp/wp3-release-and-mixing/).
[^2]: [Xie et al., “Experimental Study on Boiling Vaporization of Liquid Hydrogen in Nonspreading Pool,” *Processes* 11, 1415 (2023)](https://doi.org/10.3390/pr11051415).
[^3]: [Verfondern & Dienhart, “Experimental and theoretical investigation of liquid hydrogen pool spreading and vaporization,” *International Journal of Hydrogen Energy* 22, 649–660 (1997)](https://doi.org/10.1016/S0360-3199(96)00204-2).
[^4]: [Batt, “Modelling of Liquid Hydrogen Spills,” HSE RR985 (2014)](https://www.hse.gov.uk/Research/rrhtm/901-1000.htm).
[^5]: [Verfondern & Dienhart, “Pool spreading and vaporization of liquid hydrogen,” *International Journal of Hydrogen Energy* 32 (2007)](https://juser.fz-juelich.de/record/59057).
[^6]: [Middha, Ichard & Arntzen, “Validation of CFD modelling of LH2 spread and evaporation against large-scale spill experiments,” *International Journal of Hydrogen Energy* 36, 2620–2627 (2011)](https://doi.org/10.1016/j.ijhydene.2010.03.122).
