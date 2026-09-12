# Changelog

## 0.2.0.dev0 — unreleased

- Stage C reinforcement completed (2026-09-11) with integrated decision
  `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE` for the frozen declared-ground-inflow, horizontal,
  smooth-axisymmetric scope. The earlier provisional audit status is resolved;
  see `docs/stage-c-completion-report.md` for the qualified scope and limits.
- Fixed unledgered deletion of sub-dry-depth liquid and separated numerical wet
  area from the reported observation footprint. Added explicit numerical-mass
  adjustment, interval/last-substep evaporation, input echo and software provenance.
- Fixed `zero_radial_momentum_vapor` as the physics-declared default evaporation
  momentum closure; retained liquid-velocity carry-off only as structural sensitivity.
- Added aligned source-annulus spatial and coupled `dr`-`dt` verification. Fine-grid
  radius change is zero and liquid-inventory change is below 0.30%.
- Added a same-case-thermal-input-constrained HSE Test 6 radius assessment:
  0.92 m end radius and 19 s thermocouple-defined dryout. The condensed-air-solid
  expansion/retraction pulse remains outside the model and is explicitly non-gating.
- Added an axisymmetric radial finite-volume shallow-layer solver with local
  wet-contact age, laminar/Chezy friction, annular or central declared inflow,
  non-negative evaporation and an auditable mass ledger.
- Added separately named semi-infinite-solid and limited short-duration water
  heat-transfer closures.
- Reproduced Xie et al. (2023) Figure 11 evaporation velocity: 7.74% mean and
  10.76% maximum absolute relative error over nine experimental points.
- Validated radius transfer on held-out Dienhart Trials 4 and 6: RMSE 0.137 m
  on water and 0.102 m on aluminium; both 10–60 s continuous-film video bands
  have 100% coverage.
- Added a one-command validation run, provenance manifests, source hashes,
  comparison CSVs and figures. All 50 numerical/contract tests pass; the audited
  micro-inflow relative unledgered residual is about 8e-16.
- Retained PRESLHY repeated-fill comparisons as a conditional stress diagnostic
  because a measured inlet history is unavailable. Withdrew the earlier 1.173
  ratio caused by joining distinct temperature and scale clocks by row.

- Renamed the project and import package to **DynamicLH2PoolX** (`dynamiclh2poolx`)
  to make the time-dependent scope explicit and avoid collision with the released
  `lh2poolx` package. No in-place upgrade
  compatibility is implied across the distinct distribution names.

- Added the explicit `quasi_steady` compatibility entry point while preserving
  `evaluate_pool_source` and the v0.1 `PoolSource` schema.
- Documented units on public data objects and added finite, physical-bound
  validation for release, substrate, and thermodynamic inputs.
- Added Stage-A numerical-contract tests and an implementation/design record.
- Added the bounded fixed-area route with a serialisable ledger, exact
  conduction integration and empty-pool protection.
- Historical, superseded: added a no-fit restricted comparison against 42 connected
  PRESLHY E3.4 Concrete02 derived flux points. The recorded median predicted /
  observed ratio was 1.173; withdrawn after the instrument clock audit.

## 0.1.0 — 2026-09-09

- First public release.
- Isenthalpic LH2 flash with CoolProp.
- Explicit deposition fraction and quasi-steady ground-conduction source term.
- Confined-pool accumulation status to prevent use as an unqualified steady source.
- Optional adapters supplied by SLABx and DEGADISx; no dispersion model is a dependency.
