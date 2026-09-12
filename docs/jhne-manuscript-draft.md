# 한국수소및신에너지학회지 투고 초안

이 문서는 DynamicLH2PoolX의 검증·배포 기록을 학술 논문 형식으로 재구성한
초안이다. 수치와 주장 범위는 `docs/stage-c-completion-report.md` 및 추적되는
`data/stage_c_evidence.json`을 우선한다. 전체 실행 manifest와 그림은 검증
스크립트 실행 시 `outputs/stage_c/`에 생성된다. 저자 순서, 소속, 연구비,
감사문은 실제 기여 기록을 확인한 뒤 확정한다.

## 제목

### 국문

선언된 지표 도달 유입을 위한 액체수소 풀의 동적 축대칭 얕은층 모델 개발 및
제한적 검증

### English

Development and Restricted Validation of a Dynamic Axisymmetric Shallow-Layer
Model for Liquid-Hydrogen Pool Source Terms from Declared Ground Inflow

**Manuscript type:** Original research article

**Suggested classification:** Hydrogen safety and sensors; combustion, engine,
and heat transfer

## Abstract (150 words maximum)

Liquid-hydrogen consequence models require a traceable source term between
ground-reaching liquid and downstream dispersion. This study develops
DynamicLH2PoolX, a conservative axisymmetric shallow-layer model for a declared
liquid-to-ground inflow. It couples radial spreading, contact-age heat transfer,
evaporation, and an auditable mass ledger while separating computational wet
area from the reported footprint. Analytical contact-age integration is used
for a semi-infinite solid closure, with a short-duration constant-flux closure
for water. The 1.0e-7 kg conservation regression gives a relative unledgered
residual of 7.94e-16. JUEL holdout radius RMSEs are 0.1374 m for water Trial 4
and 0.1016 m for aluminium Trial 6, with 100% coverage of the declared video
bands. A constrained HSE Test 6 assessment gives 0.92 m at release end and 19 s
thermocouple-defined dryout. Impact, asymmetric deposition, condensed-air
deposition, and atmospheric dispersion are outside the model scope.

**Keywords:** liquid hydrogen (액체수소); pool spreading (풀 확산); evaporation
source term (증발 source term); shallow-layer model (얕은층 모델); mass
conservation (질량보존); hydrogen safety (수소 안전)

## 1. Introduction

Liquid hydrogen (LH₂) release assessments require a source term that is both
physically interpretable and reproducible. The source term is not identical to
the initial pressurised jet: a deposition or impact model must first determine
how much liquid reaches the ground and with what spatial and temporal
distribution. The present work addresses the subsequent, explicitly bounded
problem. The input is therefore a declared liquid-to-ground mass-flow history,
not an inferred jet-impact result.

Published LH₂ experiments show that spreading and vaporisation are coupled. The
Dienhart JUEL-3155 experiments provide transient radius observations for water
and aluminium surfaces. Xie et al. provide a non-spreading evaporation-rate
comparison for a concrete surface. HSE RR985/RR986 provide a larger-scale
endpoint and dryout context, but also document features associated with
condensed-air solid deposition that are outside a smooth pool model.

The contribution of this study is a transparent numerical route with four
properties: (i) conservative radial finite volumes for the shallow-layer
equations, (ii) local contact-age heat transfer integrated analytically at the
singular wetting start, (iii) explicit separation of physical wet state from the
observation operator used to report a visible front, and (iv) a machine-readable
mass ledger containing inflow, evaporation, domain escape, numerical adjustment,
and residual terms. The validation claim is intentionally restricted to the
declared-ground-inflow, horizontal, smooth-axisymmetric component scope.

## 2. Model formulation

### 2.1 State variables and geometry

The computational domain is a level, unconfined radial domain divided into
annular finite volumes. The cell state is liquid depth `h`, radial momentum
`hu`, and cumulative local contact age `a`. The source is either a parabolic
central profile or an explicitly declared uniform annulus. The annulus used in
the JUEL comparisons represents the 0.4 m catch-bowl diameter as a 0.18--0.22 m
source ring.

### 2.2 Governing equations

The shallow-layer equations are written as

```text
∂h/∂t + (1/r) ∂(r h u)/∂r = s - e

∂(h u)/∂t + (1/r) ∂[r(h u² + g' h²/2)]/∂r
    = g' h²/(2r) - F_f.
```

Here `s` is the declared mass inflow divided by liquid density and source area,
`e` is the local evaporated depth rate, `g'` is reduced gravity, and `F_f` is
the viscous/Chezy friction closure. Water uses
`g' = g(1-rho_LH2/rho_water)`; a solid surface uses `g' = g`.

The numerical flux is a conservative Rusanov flux. The time step is bounded by
the configured maximum and a CFL condition. A positive depth smaller than the
reporting threshold remains in the conserved state. If positivity clipping is
ever required, the signed volume adjustment is recorded in the ledger rather
than silently discarded. Liquid crossing the outer boundary is accumulated as
`escaped_domain_mass_kg`.

### 2.3 Heat-transfer and evaporation closures

For a homogeneous solid, local contact-age conduction is represented by

```text
q(a) = k (T0 - Tsat) / sqrt(pi alpha a),
```

with optional declared heat-flux multiplier and cap. The interval integral is
evaluated analytically, so the integrable `a = 0` singularity does not depend on
the output spacing. For the short-duration water comparison, a constant heat
flux is supplied with an explicit calibration label; this closure is limited to
the approximately 50--60 s regime supported by the cited JUEL comparison.

The default evaporation-momentum closure is
`zero_radial_momentum_vapor`, fixed before the reinforced comparisons from the
JUEL formulation with zero organised radial velocity of departing vapour. The
`liquid_velocity_carryoff` option is retained only as a structural sensitivity.

### 2.4 Observation operator and mass ledger

The physical wet area is the sum of cells whose depth exceeds the declared
retention threshold. The reported radius is the outer cell face for which depth
exceeds the configured front-detection depth. These quantities are deliberately
not interchangeable. Each output record contains both areas, both evaporation
averages (interval mean and last internal step), closure identifiers, software
versions, and the following balance:

```text
M_initial + M_inflow + M_numerical_adjustment
  = M_evaporation + M_escaped + M_liquid + residual.
```

## 3. Validation protocol

The protocol and source identifiers were frozen before the reinforced runs.
Source PDFs are not redistributed; their SHA256 hashes and the digitised
observation files are recorded in the manifests.

### 3.1 Numerical verification (C0--C1)

The C0 regression cases target the former loss of sub-threshold liquid and the
confusion between physical wet area and reported footprint. C1 varies aligned
`dr` and coupled `dr--dt` pairs, checks two domain radii, and separates front
detection depth from solution convergence. The fine-change gates are 0.02 m for
radius and 2% for liquid inventory and cumulative evaporation.

### 3.2 JUEL calibration and holdout (C2)

Water Trial 3 and aluminium Trial 5 are used only to predeclare one surface
parameter each. Water Trial 4 and aluminium Trial 6 are held out. Video-band
coverage is evaluated against the declared smooth continuous-film intervals.
Because there is one calibration trial per material, trial-bootstrap confidence
intervals are not claimed. Digitisation intervals and predeclared parameter
sensitivities are reported instead.

### 3.3 HSE endpoint assessment (C3)

RR985/RR986 Test 6 is treated as a same-case-thermal-input-constrained endpoint
assessment. The concrete properties and initial ground temperature are taken
from the cited case without fitting them to the radius observations. The
end-of-release radius and thermocouple-defined dryout are gates; the full
trajectory and the condensed-air expansion/retraction pulse are diagnostics.

## 4. Results and discussion

### 4.1 Conservation and state/observation separation

The 1.0e-7 kg inflow regression retains the liquid in the inventory ledger. The
relative unledgered residual is `7.94e-16`, and the cumulative numerical
adjustment is zero. In the independent wet/reporting regression, 0.635 kg of
liquid remains physically present and the wet-area heat flux is 754.77 W m⁻²
even when the configured reported footprint is zero. This demonstrates that a
measurement threshold cannot erase the physical state or evaporation term.

### 4.2 Numerical refinement

| Comparison | Radius change | Liquid inventory change | Cumulative evaporation change |
|---|---:|---:|---:|
| `dr: 0.01 -> 0.005 m`, fixed `dt` | 0.000000 m | 0.2932% | 0.00377% |
| coupled `dr=dt: 0.01 -> 0.005` | 0.000000 m | 0.2923% | 0.00376% |

The equal reported radius is not a six-decimal rounding artefact: both aligned
solutions return the same cell-face observation radius. Domain-radius checks
show no boundary escape. Changing the reporting depth from 0.5 to 1.0 mm gives
0.47, 0.45, and 0.44 m, respectively; this is reported as observation-operator
sensitivity rather than numerical error.

### 4.3 JUEL holdout comparisons

| Surface and trial | Role | n | RMSE (m) | MAE (m) | Bias (m) | Video-band coverage |
|---|---|---:|---:|---:|---:|---:|
| Water Trial 4 | holdout | 9 | 0.1374 | 0.1222 | -0.0778 | 100% |
| Aluminium Trial 6 | holdout | 10 | 0.1016 | 0.0920 | +0.0040 | 100% |

The aluminium multiplier remains the predeclared Trial 5 value of 0.40. A value
of 0.45 gives a slightly lower holdout RMSE, but it is not selected after seeing
the holdout. This preserves the calibration/holdout separation. The water
closure is not extrapolated beyond the short-duration evidence window.

### 4.4 HSE endpoint assessment

The calculated end-of-release radius is 0.92 m, within the digitised 0.9--1.0 m
interval. Thermocouple-defined dryout occurs 19 s after release termination,
within the 12--22 s interval. The maximum absolute unledgered residual is
`8.24e-13 kg`; numerical adjustment and escaped mass are both zero.

The complete trajectory RMSE is 0.438 m. The observed 1.3--1.4 m
expansion/retraction pulse, attributed by RR985 to condensed-air solid
deposition, is not reproduced. It is therefore a structural limitation and not
a passed trajectory gate.

### 4.5 Closure and parameter sensitivity

At 60 s, the default and alternative evaporation-momentum closures return
approximately 0.45 m and 0.49 m, respectively. The predeclared water heat-flux
sensitivity of 180, 200, and 220 kW m⁻² gives holdout RMSEs of 0.1272, 0.1374,
and 0.1497 m. The aluminium multipliers 0.35, 0.40, and 0.45 give 0.1097,
0.1016, and 0.1004 m. These are parameter-sensitivity intervals, not confidence
intervals.

The historical fixed-area route remains an algorithmic baseline for heat-transfer
and mass-balance behaviour, but it has no spreading state and must not be used as
a direct radius comparator. The dynamic route and the fixed-area route are
therefore reported as complementary source-term components rather than merged
into one unqualified validation score.

## 5. Limitations and intended use

The model is qualified only for declared ground-reaching inflow on a horizontal,
unconfined, smooth-axisymmetric surface. It does not predict jet impact,
deposition fraction, splashing, asymmetric branches, detached liquid pieces,
slopes, drains, dikes, barriers, complex terrain, condensed-air deposition, or
atmospheric dispersion. The water constant-flux closure is limited to the
approximately 50--60 s comparison regime. The preceding FFI source
reconstruction continues to use the static LH2PoolX v0.1.2 observed-footprint
route; the dynamic results are not a retroactive replacement.

## 6. Conclusions

DynamicLH2PoolX provides a reproducible dynamic LH₂ pool source-term route for a
declared liquid-to-ground inflow. C0 conservation and state/observation fixes,
C1 refinement checks, JUEL holdout comparisons, and a constrained HSE endpoint
assessment establish a restricted component-level evidence chain. The two JUEL
holdouts reproduce the declared smooth-film radius bands, and the mass ledger
closes to numerical precision. The result is suitable for source-term studies
and downstream dispersion coupling within the stated scope, but it is not a
validation of the complete LH₂ spill-formation or atmospheric-consequence chain.

## Figure and table plan for the final manuscript

1. **Fig. 1:** model control volume, source annulus, wet area, and reported
   front-depth observation operator.
2. **Fig. 2:** computational workflow from declared inflow to ledger and source
   term.
3. **Fig. 3:** C1 grid/time refinement and front-depth sensitivity.
4. **Fig. 4:** JUEL water Trial 4 radius history with digitisation intervals.
5. **Fig. 5:** JUEL aluminium Trial 6 radius history with digitisation intervals.
6. **Fig. 6:** HSE Test 6 endpoint and structural expansion/retraction diagnostic.
7. **Table 1:** governing assumptions and closure identifiers.
8. **Table 2:** numerical verification metrics.
9. **Table 3:** calibration/holdout metrics and sensitivity ranges.

Existing source figures and generated comparisons are in `outputs/spreading_validation/`
and `outputs/stage_c/hse_test6/`. Every final figure must retain SI units and an
English caption.

## Data and code availability

The implementation, tests, validation protocol, digitised derivative points,
the tracked evidence snapshot (`data/stage_c_evidence.json`), and reproducibility
scripts are available in the public
[DynamicLH2PoolX repository](https://github.com/lyullee/DynamicLH2PoolX). The
current reproducibility artifact is published on
[PyPI](https://pypi.org/project/dynamiclh2poolx/) as `0.2.0.dev0`. Copyrighted
source PDFs are identified by hash and local path but are not redistributed.

## References for the final manuscript

1. Xie et al., “Experimental Study on Boiling Vaporization of Liquid Hydrogen in
   Nonspreading Pool,” *Processes*, 11, 1415 (2023), doi:
   [10.3390/pr11051415](https://doi.org/10.3390/pr11051415).
2. Dienhart, *Tiefkalte Flussiggas-Lachen*, JUEL-3155 (1995), persistent record:
   [JUEL-3155](https://juser.fz-juelich.de/record/860517).
3. Verfondern and Dienhart, “Experimental and theoretical investigation of
   liquid hydrogen pool spreading and vaporization,” *International Journal of
   Hydrogen Energy*, 22, 649--660 (1997), doi:
   [10.1016/S0360-3199(96)00204-2](https://doi.org/10.1016/S0360-3199(96)00204-2).
4. Batt, *Modelling of Liquid Hydrogen Spills*, HSE RR985 (2014),
   [HSE report catalogue](https://www.hse.gov.uk/Research/rrhtm/901-1000.htm).
5. Verfondern and Dienhart, “Pool spreading and vaporization of liquid
   hydrogen,” *International Journal of Hydrogen Energy*, 32 (2007), persistent
   record: [Jülich record](https://juser.fz-juelich.de/record/59057).
6. Friedrich et al., “PRESLHY Experiment series 3.4,” KIT (2020/2023), doi:
   [10.35097/1319](https://doi.org/10.35097/1319).
7. Takeno et al., “Evaporation rates of liquid hydrogen and liquid oxygen spilled
   onto the ground,” *Journal of Loss Prevention in the Process Industries*, 7,
   425--431 (1994), doi:
   [10.1016/0950-4230(94)80061-8](https://doi.org/10.1016/0950-4230(94)80061-8).
