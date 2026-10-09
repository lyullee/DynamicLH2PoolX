# Observed-footprint source route

## Purpose

evaluate_observed_footprint_source is a narrow source-term conversion for the
situation in which a record constrains the footprint of liquid hydrogen on a
solid surface, but does not resolve the release-to-ground handoff. It takes a
declared circular-equivalent radius and returns the heat-limited evaporation
source for one declared elapsed time.

It is deliberately separate from the v0.1 forward route:

- evaluate_pool_source: declared release rate + pressure +
  deposition_fraction -> quasi-steady area.
- evaluate_observed_footprint_source: declared equivalent radius ->
  quasi-steady evaporation source.

Neither route predicts jet impact, liquid deposition, splash, droplets,
drainage, barriers or a time-resolved pool trajectory.

## Calculation

At a declared elapsed time, solid semi-infinite conduction gives a capped heat
flux. The evaporation flux is the heat flux divided by the saturated LH2
latent heat. For a declared circular-equivalent radius, the source area is pi
times radius squared and the evaporation rate is area times evaporation flux.

required_liquid_ground_rate_kg_s equals the evaporation rate only as the
quasi-steady balance required to sustain that fixed footprint. It is not a
measured liquid deposition rate and must not be used to infer one.

## FFI use boundary

The FFI large-scale LH2 test report states that vertical-release pools were
limited to approximately 0.5-1.0 m from the release point and that fog
prevented precise visual confirmation. Thus, use 0.5 m and 1.0 m as separate
conditional radial-extent inputs. Do not report their midpoint as an observed
pool radius, and do not tune a deposition fraction to reproduce either bound.

The route is suitable for making the source assumption visible before passing
the resulting area and evaporation rate to a ground-cloud dispersion model.
It is not validation of FFI pool area, evaporation rate, source duration or
sensor concentration.
