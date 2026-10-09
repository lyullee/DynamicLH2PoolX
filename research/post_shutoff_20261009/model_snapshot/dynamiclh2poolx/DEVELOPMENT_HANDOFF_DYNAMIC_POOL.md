# DynamicLH2PoolX v0.2 — dynamic LH2 pool-model development handoff

> **Implemented and validated 2026-09-11.** The authoritative implementation
> and evidence record are now `src/dynamiclh2poolx/dynamic_pool.py`,
> `docs/dynamic-model-design.md`, and `docs/dynamic-validation-report.md`.
> The remaining text is retained as the original development specification.

## Copy-paste task instruction for the next session

> Develop **DynamicLH2PoolX v0.2** from the present quasi-steady, evidence-qualified source-term package into a transparent **time-dependent LH2 pool spreading and evaporation model**.  Keep the scope deliberately narrow: an unconfined, axisymmetric LH2 pool on an unobstructed, level, homogeneous solid surface or water surface, given a declared liquid-to-ground inflow history.  Do not claim to predict a jet-impact footprint, deposition fraction, splash/droplet transport, drainage, barriers, slopes, or complex geometry.  Preserve v0.1 behaviour as a separately callable quasi-steady route.  Implement in small validated stages; do not tune coefficients to downstream hydrogen concentrations.  Deliver documented equations, unit tests, reproducible validation scripts, figures/tables, and an explicit applicability statement before changing the package's scientific claims.

---

## 1. Why this work exists

The released package (`v0.1.0`) calculates a **quasi-steady conditional pool source term**:

`declared release -> isenthalpic flash -> declared deposition fraction -> heat-limited evaporation -> equilibrium pool area/source`

It intentionally does **not** calculate a pool trajectory.  That limitation is correct for the current dispersion-comparison paper, but a dynamic pool model is a viable independent software and methods-research project.

The target of v0.2 is narrower and scientifically defensible:

`declared liquid inflow to a known point/area -> pool radius(t), depth(t), liquid inventory(t), evaporation rate(t), and gas source term(t)`

The package is **not** to infer how a pressurised LH2 jet becomes that liquid inflow.  The input must remain explicit as `liquid_to_ground_rate(t)` or as an externally justified deposition model.

## 2. Non-negotiable scientific boundary

### In scope

- LH2 thermophysical properties via CoolProp.
- Axisymmetric, shallow-layer, unconfined spreading on a horizontal homogeneous substrate.
- Time-dependent mass balance and pool geometry.
- Heat transfer from a solid substrate or water substrate through separately named closures.
- Evaporation and optional explicit air-condensation/freeze **sensitivity** closure, only after its assumptions are documented.
- A reproducible source-term output for downstream SLABx, DEGADISx, or CFD.

### Out of scope unless independently added and validated

- Jet breakup, impingement, splash, droplet trajectories, and deposition fraction prediction.
- Pool motion in complex terrain, dikes, drains, barriers, porous ground, or buildings.
- A full 3-D gas cloud or atmospheric dispersion calculation.
- Automatic calibration to concentration, LFL distance, or a particular release experiment.
- Statements such as “validated for all LH2 spills” or “predicts actual pool footprint after an impact.”

If a requested feature crosses this boundary, add it as a separately named experimental route with its own evidence record.  Do not silently extend the default model.

## 3. Present repository state

Repository: `C:\Users\Lyul\Desktop\LH2PoolX`

Current development distribution: `dynamiclh2poolx` (`0.2.0.dev0`). The released
`lh2poolx` package remains a separate historical distribution.

Important current files:

- `src/dynamiclh2poolx/pool.py` — quasi-steady implementation.
- `tests/test_pool.py` — current tests.
- `README.md` — existing scientific boundary.

Current v0.1 inputs are release rate, storage pressure, deposition fraction, elapsed time and substrate.  It uses CoolProp for an isenthalpic saturated-liquid flash calculation, a semi-infinite ground-conduction relation, and an optional critical heat-flux cap.  Preserve this API and result type as the `quasi_steady` compatibility route.

## 4. Required model architecture

Do not bury all physics in one function.  Use explicit modules and typed data objects.

Suggested package layout:

```text
src/dynamiclh2poolx/
  thermodynamics.py     # CoolProp calls; flash and saturation state
  inflow.py             # declared liquid-to-ground histories
  substrates.py         # solid/water substrate properties and closures
  spreading.py          # axisymmetric shallow-layer spreading closures
  evaporation.py        # heat/mass-transfer and cryogenic options
  dynamic_pool.py       # ODE state, solver, events, result ledger
  adapters.py           # optional source-term export only
  evidence.py           # model version, closure IDs, applicability status
```

### 4.1 Minimum state vector

At minimum integrate:

\[
M_l(t),\quad R(t),\quad h(t)=\frac{M_l(t)}{\rho_l\pi R(t)^2}
\]

with a declared inflow \(\dot m_{l,\mathrm{in}}(t)\):

\[
\frac{dM_l}{dt}=\dot m_{l,\mathrm{in}}(t)-\dot m_{\mathrm{evap}}(t).
\]

The radius evolution must come from a cited shallow-layer/gravity-spreading closure, not from an instantaneous equilibrium area.  State the chosen closure and every assumption in code/docstrings.

### 4.2 Required outputs

Each dynamic result must contain a time-indexed ledger:

- time;
- liquid inflow and accumulated liquid mass;
- radius, area and mean depth;
- pool temperature and saturation properties;
- substrate heat flux and evaporative mass flux;
- total evaporation rate;
- closure identifiers and warnings;
- source-status field: `within_declared_scope`, `input_limited`, or `out_of_scope`.

Pool disappearance must be handled as an event, not as negative mass, negative radius, or a numerical extrapolation.

## 5. Development sequence — do not skip stages

### Stage A — preserve v0.1 and establish the numerical contract

1. Add regression tests that reproduce all v0.1 numerical outputs.
2. Introduce a stable public result schema; add units to every public field.
3. Add input validation for non-negative inflow, time ordering, substrate properties and physical bounds.
4. Add mass-conservation tests for no-inflow/no-evaporation and prescribed constant evaporation cases.

**Acceptance:** existing v0.1 tests pass unchanged and new conservation tests pass to a documented tolerance.

### Stage B — dynamic, nonspreading bounded pool

1. Implement a fixed-area mode with \(R\) prescribed.
2. Solve the mass balance with the current semi-infinite solid-conduction closure.
3. Validate first against the open 2023 concrete nonspreading-pool study using only pool mass-loss and substrate-temperature observables.
4. Do not fit a heat-transfer coefficient separately for each run.  If a parameter must be estimated, declare it once, use a calibration/validation split, and report it as a limited empirical closure.

**Acceptance:** plot measured and calculated mass or evaporation rate versus time; report RMSE/MAE, bias, simulation conditions, and which data were digitised rather than supplied as raw files.

### Stage C — axisymmetric spreading on a solid surface

1. Implement one documented shallow-layer spreading closure.
2. Couple it to the dynamic mass/evaporation balance without assuming instant equilibrium area.
3. Validate radius/area trajectories before presenting downstream gas-source results.
4. Use the controlled LH2 water/aluminium spreading experiments of Verfondern and Dienhart as the primary historical benchmark; digitise figures only with a traceable digitisation record if raw data cannot be obtained.

**Acceptance:** `R(t)`, `A(t)`, `M(t)` and \(\dot m_{evap}(t)\) plots with uncertainty/read-off limitations visibly labelled.

### Stage D — substrate variants and physical stress tests

1. Keep solid ground and water as different closures; never label one generic “ground.”
2. Add analytical limiting-case tests: zero inflow, zero heat flux, constant inflow, very large heat-transfer limit, and empty-pool event.
3. Demonstrate parameter sensitivity to substrate conductivity/diffusivity, initial substrate temperature and inflow rate.
4. State whether air condensation/freezing is excluded, included as a switch, or treated as an uncertainty envelope.

**Acceptance:** model behaves monotonically and conserves mass across stated limiting cases.  Any non-monotonic physical response must be explained and tested.

### Stage E — independent system-level check

Use NASA Test 6, HSL/BAM, or another public large spill only as a **system-level check** after component validation.  Compare quantities genuinely observed: reported pool scale/lifetime, temperature, and/or downstream source consistency.  Do not call this a validation of every internal closure.

## 6. Evidence plan and datasets

Use the following evidence hierarchy in documentation and release notes.

| Tier | Dataset | Appropriate observable | Role |
|---|---|---|---|
| A | 2023 concrete nonspreading-pool study | mass loss / evaporation; substrate temperature | validate heat-transfer and evaporation submodel |
| A/B | Verfondern–Dienhart water/aluminium tests | pool radius/area and vaporisation histories | validate spreading plus evaporation coupling |
| B | HSE/HSL RR985 and related releases | pool-radius evolution, near-pool temperature | independent constrained comparison; some quantities not directly measured |
| B | NASA White Sands Test 6 | reported pool scale/lifetime and downwind cloud observations | system-level source-to-cloud consistency only |
| C | FFI/PRESLHY downward releases | declared source and downstream concentration | conditional integration examples, not pool validation |

Key public references:

- Verfondern & Dienhart, 1997, *Experimental and theoretical investigation of liquid hydrogen pool spreading and vaporization*, DOI: `10.1016/S0360-3199(96)00204-2`.
- Verfondern & Dienhart, 2007, *Pool spreading and vaporization of liquid hydrogen*, DOI: `10.1016/j.ijhydene.2006.01.016`.
- Zhang et al., 2023, *Experimental Study on Boiling Vaporization of Liquid Hydrogen in Nonspreading Pool*, DOI: `10.3390/pr11051415`.
- Batt, 2014, HSE RR985, *Modelling of liquid hydrogen spills*.
- Middha et al., 2011, *Validation of CFD modelling of LH2 spread and evaporation against large-scale spill experiments*, DOI: `10.1016/j.ijhydene.2010.03.122`.

Before digitising any figure, create `data/README.md` recording source, figure/table number, units, digitisation method, point count, date, and restrictions.  Never redistribute copyrighted data unless its licence explicitly permits it.

## 7. Scientific rules

1. **No downstream concentration fitting.**  Do not tune pool parameters to make SLABx, DEGADISx or CFD concentration contours match.
2. **Separate validation observables.**  Radius validates spreading; mass loss validates evaporation; temperature validates heat transfer.  A good gas-cloud result alone does not validate the pool model.
3. **Retain input uncertainty.**  If liquid deposition is unknown, it stays an input envelope.  The model must not infer it from desired outcomes.
4. **No universal accuracy statement.**  Every result must name substrate, geometry, inflow definition, time interval and evidence status.
5. **Do not merge solid and water behaviour.**  Water/RPT and ice processes need their own route and evidence.
6. **Use SI units internally.**  Convert only at input/output boundaries.

## 8. Required tests and reproducibility artefacts

Required automated tests:

- thermodynamic property sanity checks at saturation;
- flash fraction physical bounds;
- mass conservation over every dynamic run;
- non-negative radius, depth, mass and evaporation;
- monotonic empty-pool event;
- fixed-area regression against v0.1 where assumptions coincide;
- deterministic solver results under a fixed tolerance;
- serialisation/reload of a result ledger.

Required reproducibility artefacts:

- `scripts/run_validation_*.py` for each evidence tier;
- machine-readable input files under `data/derived/` or a non-redistributable manifest;
- `outputs/` excluded from source distributions unless they are small curated benchmark files;
- a single command documented in README to reproduce every reported table and figure;
- environment lock or fully pinned dependency ranges.

## 9. Release criteria for v0.2

Do not publish v0.2 until all are true:

- API reference distinguishes `quasi_steady` and `dynamic` routes.
- At least one heat/evaporation validation and one spreading validation are reproducible.
- Results report data provenance and digitisation uncertainty where relevant.
- README contains an applicability map and explicit exclusions.
- CI runs all unit tests on a clean environment.
- Semantic version, changelog and citation metadata are updated.
- A release note states that v0.2 does not predict jet impact/deposition without an external model.

## 10. What a credible first dynamic-model paper/release may claim

Acceptable claim:

> “DynamicLH2PoolX provides an open, time-dependent, axisymmetric source-term model for declared LH2 liquid inflow to an unobstructed horizontal substrate.  Its heat-transfer and spreading components are assessed against the stated public experiments, and its outputs are traceable inputs for downstream dispersion models.”

Unacceptable claim:

> “DynamicLH2PoolX predicts the full consequences of arbitrary LH2 releases or the actual pool footprint after a downward jet impact.”

## 11. First-session checklist

- [x] Read this handoff and `README.md` before editing physics.
- [x] Run current tests and record the baseline package version.
- [x] Create a design note selecting one shallow-layer closure and its governing equations.
- [x] Preserve Stage A and the quasi-steady compatibility route.
- [x] Acquire and record evidence sources before fitting or validating anything.
- [x] Build bounded fixed-area dynamic mode before spreading mode.
- [x] Restrict each closure to the measurements that support it.
