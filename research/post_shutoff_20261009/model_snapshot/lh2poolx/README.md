# LH2PoolX

LH2PoolX calculates an evidence-qualified, quasi-steady liquid-hydrogen
(LH2) pool source term for one declared time window. It is an upstream input
to a dispersion calculation. It is **not** a dispersion solver, an
impact/impingement model, or a general transient pool-spreading model.

The package makes the source assumption explicit. It does not silently replace
unknown liquid deposition, pool growth, inventory, or drainage with a fitted
parameter.

## 1. Select the appropriate calculation route

| Information available to the analyst | Function | Meaning of its output |
| --- | --- | --- |
| Release rate, storage pressure, and a declared fraction of liquid reaching the ground | evaluate_pool_source | Quasi-steady pool source consistent with the declared release-to-ground assumption |
| A reported or site-declared pool footprint, but no defensible liquid-deposition fraction | evaluate_observed_footprint_source | Conditional evaporation source for that footprint; not a reconstructed impact or pool history |

Neither route predicts an unknown impingement footprint. For a downward jet,
the impact, droplet, and release-to-ground handoff must be separately
justified before the declared-release route is used.

## 2. Install

LH2PoolX supports Python 3.10 or later. CoolProp is installed automatically.

~~~
python -m pip install --upgrade lh2poolx
python -c "import lh2poolx; print(lh2poolx.__version__)"
~~~

For a reproducible calculation, record the printed LH2PoolX version, the
CoolProp version, all source inputs, the selected route, and source_status.

## 3. Route 1: declared release and deposition fraction

Use this route only when the release-to-ground handoff is an explicit scenario
input. The calculation chain is:

1. saturated-liquid, isenthalpic flash from the declared storage pressure to
   the declared ambient pressure;
2. liquid mass reaching the ground after the explicit deposition_fraction;
3. heat-limited evaporation flux from a semi-infinite ground-conduction
   relation, subject to the LH2 critical-heat-flux cap; and
4. an unconfined equilibrium area whose evaporation balances the declared
   liquid input.

~~~
from lh2poolx import LH2Release, evaluate_pool_source

release = LH2Release(
    rate_kg_s=0.1055,          # declared upstream LH2 release rate
    storage_pressure_barg=1.0, # storage gauge pressure
    deposition_fraction=0.50, # declared liquid fraction reaching the ground
)

source = evaluate_pool_source(
    release,
    elapsed_s=300.0,           # time since pool formation for ground conduction
    ambient_temperature_K=282.0,
)

print(f"flash fraction:     {source.flash_vapour_fraction:.3f}")
print(f"liquid to ground:   {source.liquid_to_ground_kg_s:.4f} kg/s")
print(f"pool radius:        {source.radius_m:.3f} m")
print(f"pool area:          {source.area_m2:.3f} m2")
print(f"evaporation source: {source.evaporation_rate_kg_s:.4f} kg/s")
print(f"status:             {source.source_status}")
~~~

### Inputs

| Input | Units | Interpretation |
| --- | --- | --- |
| rate_kg_s | kg/s | Declared upstream LH2 release rate |
| storage_pressure_barg | bar(g) | Saturated-liquid storage pressure used in the flash calculation |
| deposition_fraction | - | Analyst-declared fraction of post-flash liquid reaching the ground; it is neither predicted nor fitted |
| elapsed_s | s | Time used in the transient ground-conduction flux; this does not create a full pool time-history model |
| ambient_temperature_K | K | Surface/ambient temperature for the heat-transfer relation |
| max_radius_m | m, optional | Physical confinement radius. If it constrains the pool, an inventory model is required |

### Read the result correctly

evaporation_rate_kg_s is the mass source to pass to a downstream dispersion
route. It is not necessarily the original upstream release rate.

If source.confined is True, or source_status is
confined_pool_requires_inventory_model, the declared radius cannot evaporate
all of the liquid input. liquid_accumulation_rate_kg_s then identifies the
unremoved liquid rate. Do not use that case as an unqualified steady source:
add an inventory, spreading, drainage, or overflow model.

## 4. Route 2: declared observed footprint

Use this route when a record constrains pool extent more credibly than it
constrains the fraction of the release that deposited on the ground. It
deliberately has no release rate or deposition_fraction input.

~~~
from lh2poolx import evaluate_observed_footprint_source

# Retain both bounds when a record reports a range. Do not use a midpoint.
for radius_m in (0.5, 1.0):
    source = evaluate_observed_footprint_source(
        equivalent_radius_m=radius_m,
        elapsed_s=300.0,
        ambient_temperature_K=282.0,
    )
    print(
        f"R = {source.equivalent_radius_m:.1f} m | "
        f"A = {source.area_m2:.3f} m2 | "
        f"evaporation = {source.evaporation_rate_kg_s:.4f} kg/s | "
        f"required steady liquid inflow = "
        f"{source.required_liquid_ground_rate_kg_s:.4f} kg/s"
    )
~~~

equivalent_radius_m is the radius of a circle having the declared footprint
area. It is a geometric source assumption, not a claim that the physical pool
was circular.

required_liquid_ground_rate_kg_s is the quasi-steady liquid inflow that would
sustain the calculated evaporation. It is **not** an observed deposition rate.

The FFI large-scale LH2 report describes the vertical-release pools as
remaining within roughly 0.5-1.0 m of the release point while noting that fog
prevented precise visual verification. That evidence can support a 0.5-1.0 m
conditional radial-extent envelope. It does not support fitting a single
footprint, evaporation history, or deposition fraction. See the
[FFI report](https://www.ffi.no/publikasjoner/arkiv/large-scale-leakage-of-liquid-hydrogen-lh2-tests-related-to-bunkering-and-maritime-use-of-liquid-hydrogen/21-03101.pdf).

## 5. Pass the source to a dispersion model

LH2PoolX deliberately has no dependency on SLABx, DEGADISx, or another
dispersion package. Pass only the quantities accepted by the downstream route,
along with the source assumption:

~~~
# source can be either PoolSource or ObservedFootprintSource
dispersion_input = {
    "source_mass_rate_kg_s": source.evaporation_rate_kg_s,
    "source_area_m2": source.area_m2,
    "equivalent_radius_m": (
        getattr(source, "equivalent_radius_m", None)
        or getattr(source, "radius_m", None)
    ),
    "source_status": source.source_status,
}
~~~

For the observed-footprint route, retain both envelope bounds in the
dispersion study. The outputs are alternative, declared source assumptions;
they are not a statistical confidence interval and should not be averaged into
one best source.

## 6. Output fields

| Output | Route | Meaning |
| --- | --- | --- |
| area_m2 | both | Pool footprint area used by the source calculation |
| evaporative_flux_kg_m2_s | both | Heat-limited mass flux for the declared substrate and time |
| evaporation_rate_kg_s | both | Mass source available to the downstream dispersion calculation |
| source_status | both | Machine-readable indication of the source assumption and restrictions |
| flash_vapour_fraction | declared release | Isenthalpic flash fraction from the declared storage pressure |
| liquid_to_ground_kg_s | declared release | Post-flash liquid rate multiplied by the declared deposition fraction |
| radius_m and unconfined_radius_m | declared release | Equilibrium radius after and before declared confinement |
| liquid_accumulation_rate_kg_s | declared release | Input not removed by evaporation when the pool is confined |
| equivalent_radius_m | observed footprint | Declared circular-equivalent footprint radius |
| required_liquid_ground_rate_kg_s | observed footprint | Quasi-steady inflow needed to sustain evaporation; not an observation |

## 7. Substrate and physical limits

CONCRETE_CRYOGENIC is the default effective substrate parameter set. It is tied
to the restricted PRESLHY E3.4 Concrete02 component check and must not be
treated as a universal concrete correlation. Provide another Substrate only
when its conductivity and diffusivity are independently justified for the
site and temperature range.

~~~
from lh2poolx import Substrate, evaluate_observed_footprint_source

site_substrate = Substrate(
    name="declared_site_substrate",
    conductivity_W_mK=1.5,
    diffusivity_m2_s=8.0e-7,
)

source = evaluate_observed_footprint_source(
    equivalent_radius_m=0.75,
    elapsed_s=300.0,
    substrate=site_substrate,
)
~~~

LH2PoolX does not resolve jet trajectory, impingement, splashing, droplet
transport, rainout, transient pool growth, liquid inventory, drainage,
barriers, slope, detailed boiling transitions, or three-dimensional vapour
dispersion. Use an explicit upstream model or a conditional scenario envelope
when those processes govern the decision.

## 8. Error handling and reproducibility

The package rejects non-positive mass rates, radii, elapsed times and
thermodynamic pressures, as well as deposition fractions outside 0-1. Treat an
error as an input-definition issue; do not replace an invalid value silently.

To reproduce the tests from a source checkout:

~~~
git clone https://github.com/lyullee/lh2poolx.git
cd lh2poolx
python -m pip install -e .[test]
python -m pytest -q
~~~

The concrete heat-transfer implementation has a restricted component check
against published PRESLHY E3.4 Concrete02 mass-loss windows. It is not
validation of another substrate, a complete pool-growth model, or an unknown
jet-to-ground handoff.

## 9. Citation and license

LH2PoolX is released under the MIT License. Cite the released software version
and the experimental and heat-transfer sources used in an analysis. Citation
metadata are provided in [CITATION.cff](CITATION.cff).
