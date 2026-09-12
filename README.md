# DynamicLH2PoolX

DynamicLH2PoolX is a transparent, time-dependent source-term model for a declared
liquid-hydrogen (LH₂) inflow that has already reached a horizontal surface. It
tracks axisymmetric shallow-layer spreading, local wet-contact evaporation, liquid
inventory, and an auditable mass balance. The package also retains the historical
quasi-steady LH2PoolX v0.1.2 route for reproducibility of earlier FFI calculations.

DynamicLH2PoolX does not infer how a pressurised jet becomes ground-reaching liquid.
That deposition or impact calculation must be supplied by the caller as an explicit
`DeclaredInflow` history.

## Verification status

The current release candidate has completed the restricted Stage C component scope.
The machine-readable decision is:

```text
PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE
```

This means that the declared-ground-inflow, horizontal-surface, smooth-axisymmetric
pool source-term route has passed solution checks and the stated component
comparisons. It is not a claim that all LH₂ pool formation or spill consequences
have been validated.

### Quantitative evidence

| Evidence | Result | Interpretation |
|---|---:|---|
| C0 micro-inflow conservation | relative unledgered residual `7.94e-16` | A `1.0e-7 kg` inflow remains in the inventory ledger |
| C0 wet/reporting separation | `0.635 kg` inventory retained; wet-area heat flux `754.77 W/m²` | A zero reported footprint no longer erases physical state or evaporation |
| C1 spatial refinement | `dr=0.01 → 0.005 m`: radius change `0.000000 m`, inventory change `0.2932%` | Source annulus is aligned to cell faces for the converged comparison |
| C1 coupled refinement | `dr=dt=0.01 → 0.005`: radius change `0.000000 m`, inventory change `0.2923%` | Spatial and time-step refinement are tested together |
| JUEL water Trial 4 holdout | RMSE `0.1374 m`, video-band coverage `100%` | Held-out radius comparison |
| JUEL aluminium Trial 6 holdout | RMSE `0.1016 m`, MAE `0.0920 m`, bias `+0.0040 m`, video-band coverage `100%` | Held-out radius comparison with near-zero bias |
| HSE RR985/RR986 Test 6 | end-of-release radius `0.92 m`; thermocouple-defined dryout `19 s` | Same-case-thermal-input-constrained independent radius assessment |
| HSE conservation | maximum absolute unledgered residual `<1.2e-12 kg`; numerical adjustment `0 kg`; escaped mass `0 kg` | Numerical accounting check |
| Automated tests | `50 passed` | Unit, contract, conservation, closure, and solver checks |

The HSE radius observations are digitised from a published figure and are labelled
`figure_digitised` in the manifest. The complete trajectory RMSE is `0.438 m`; the
1.3–1.4 m expansion/retraction pulse attributed to condensed-air solid deposition is
not reproduced by the smooth pool model and is reported as a structural diagnostic,
not as a passed trajectory gate.

For JUEL calibration, water Trial 3 and aluminium Trial 5 are used to freeze one
surface parameter each before applying the values to Trials 4 and 6. The aluminium
multiplier `0.40` remains the predeclared Trial 5 value even though `0.45` gives a
slightly lower holdout RMSE; the latter is not selected after seeing the holdout.
Because there is only one calibration trial per material, no trial-bootstrap 95% CI
is claimed. Digitisation intervals and predeclared parameter sensitivities are
reported instead.

See the [Stage C completion report](docs/stage-c-completion-report.md) for the full
scope statement, input basis, source IDs, sensitivity runs, and limitations. The
authoritative result is [outputs/stage_c/manifest.json](outputs/stage_c/manifest.json).

## Scope and limitations

Validated scope:

- declared liquid-to-ground inflow history;
- unconfined, horizontal, axisymmetric shallow-layer spreading;
- water or homogeneous solid surfaces with an explicitly named heat-transfer closure;
- source-term outputs for downstream dispersion calculations.

Outside the validated scope are jet impact, splash and droplet transport, deposition
fraction prediction, asymmetric branches, detached liquid pieces, slopes, drains,
dikes, barriers, complex terrain, condensed-air solid deposition, and atmospheric
dispersion. The water constant-heat-flux closure is limited to the approximately
50–60 s regime supported by the cited JUEL comparison.

The previous FFI source reconstruction continues to use the static LH2PoolX v0.1.2
observed-footprint route. DynamicLH2PoolX results must not be substituted into that
calculation without a separate, versioned coupling study.

## Installation

### From a source checkout

```powershell
python -m pip install -e .
python -m pip install -r requirements-validation.txt
python -m pytest -q
```

After the first PyPI release, the package will be installable with:

```powershell
python -m pip install dynamiclh2poolx
```

The import name is also `dynamiclh2poolx`.

## Quick start: solid surface

The model requires a time history of liquid that has already reached the ground.
Rates are in kg/s, times are in seconds, and all geometry is in metres.

```python
from dynamiclh2poolx import (
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)

surface = SolidSemiInfiniteSurface(
    name="concrete",
    conductivity_W_mK=0.88,
    diffusivity_m2_s=1.5775e-7,
    initial_temperature_K=195.7,
)

numerics = ShallowLayerNumerics(
    domain_radius_m=5.0,
    source_radius_m=0.20,
    radial_step_m=0.01,
    maximum_time_step_s=0.02,
)

inflow = DeclaredInflow(
    times_s=(0.0, 60.0),
    rates_kg_s=(0.10, 0.0),
)

result = run_dynamic_pool(
    DynamicPoolConfig(surface=surface, numerics=numerics),
    inflow,
    output_times_s=(0.0, 10.0, 30.0, 60.0, 90.0),
)

last = result.ledger[-1]
print(f"reported radius: {last.reported_radius_m:.3f} m")
print(f"liquid inventory: {last.liquid_mass_kg:.6g} kg")
print(f"mass residual: {result.mass_balance_residual_kg:.3e} kg")
```

`DeclaredInflow` uses a zero-order hold: each rate applies from its timestamp until
the next timestamp, and the last rate continues thereafter. The first timestamp must
be `0.0`, timestamps must be increasing, and rates must be non-negative.

## Choosing a surface closure

For a homogeneous solid, use local semi-infinite conduction:

```python
surface = SolidSemiInfiniteSurface(
    name="concrete",
    conductivity_W_mK=0.93,
    diffusivity_m2_s=4.8e-7,
    initial_temperature_K=266.0,
    heat_flux_multiplier=1.0,
)
```

For the short-duration empirical water route, make the evidence basis explicit:

```python
from dynamiclh2poolx import ConstantHeatFluxWaterSurface

surface = ConstantHeatFluxWaterSurface(
    heat_flux_W_m2=200_000.0,
    calibration_label="Dienhart JUEL-3155 Trial 3 water closure",
)
```

The default evaporation momentum closure is
`zero_radial_momentum_vapor`, corresponding to zero organised radial velocity of
departing vapour in the JUEL-based closure. The alternative
`liquid_velocity_carryoff` is available only for structural sensitivity:

```python
config = DynamicPoolConfig(
    surface=surface,
    numerics=numerics,
    evaporation_momentum_closure="zero_radial_momentum_vapor",
)
```

If a rough-surface retention layer is physically justified, set
`surface_retention_depth_m` in `ShallowLayerNumerics`. This is a declared physical
input, not a radius-fitting parameter.

## Understanding the result

Each `DynamicPoolLedger` row contains SI-unit fields for inflow, liquid inventory,
evaporation, spreading, and provenance. The most important fields are:

- `wet_area_m2`: computational cells containing liquid above the declared retention
  layer;
- `reported_radius_m` and `reported_area_m2`: observation-operator outputs based on
  the configured detection depth;
- `wet_area_mean_depth_m` and `wet_area_mean_evaporation_flux_kg_m2_s`: averages over
  the computational wet area, not the reported footprint;
- `interval_mean_evaporation_rate_kg_s` and
  `last_substep_evaporation_rate_kg_s`: explicitly different time averages;
- `escaped_domain_mass_kg`, `cumulative_numerical_mass_adjustment_kg`, and
  `unledgered_mass_residual_kg`: the mass-accounting audit trail;
- `evaporation_momentum_closure`, `heat_transfer_closure_id`, and
  `spreading_closure_id`: the selected physics and numerical closures.

`DynamicPoolResult.configuration_echo` and `software_versions` record the settings
and runtime versions needed to reproduce a run.

## Reproducing the validation record

### Stage C restricted component validation

The JUEL and HSE PDFs are not redistributed with the package. Supply their local
paths explicitly:

```powershell
.\.venv\Scripts\python.exe scripts/validate_stage_c.py `
  --dienhart-pdf "outputs/sources/dienhart_1995_juel3155.pdf" `
  --rr985-pdf "C:/path/to/rr985.pdf" `
  --rr986-pdf "C:/path/to/rr986.pdf"
```

This runs the C1 convergence matrix, JUEL calibration/holdout assessment, HSE Test 6
endpoint assessment, and writes hashed manifests under `outputs/stage_c/`.

### Full validation record

If the PRESLHY dataset and Xie PDF are available, run the broader component record:

```powershell
.\.venv\Scripts\python.exe scripts/validate_all.py `
  --dataset-dir "C:/path/to/PRESLHY/dataset" `
  --xie-pdf "outputs/sources/xie2023.pdf" `
  --dienhart-pdf "outputs/sources/dienhart_1995_juel3155.pdf"
```

PRESLHY repeated-fill comparisons remain a conditional stress diagnostic because a
measured ground-inflow history is unavailable. Validation outputs include comparison
tables, figures, source hashes, digitisation records, and software metadata. Source
PDFs and other copyrighted raw materials are not redistributed.

## Project layout

```text
src/dynamiclh2poolx/       package implementation
tests/                     unit and contract tests
data/                      frozen observations and validation protocols
scripts/                   reproducible validation runners
docs/                      design, audit, and completion reports
outputs/stage_c/           generated validation manifests and figures
```

## License and citation

Code is released under the MIT License. Experimental data and digitised derivative
points remain subject to their original source licences. See [CITATION.cff](CITATION.cff)
and the [Stage C completion report](docs/stage-c-completion-report.md) for the cited
JUEL, HSE, Xie, and supporting sources.
