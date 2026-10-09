# Evidence-data register

The repository does not redistribute source workbooks or PDFs. Reproduction
scripts write digitised coordinates, figures, hashes, and provenance manifests
under the ignored `outputs/` directory.

## Stage B: Xie et al. 2023 Figure 11

Source: Xie et al., *Processes* 11(5), 1415,
DOI 10.3390/pr11051415, PDF page 11, Figure 11. The paper is CC BY 4.0.

The embedded 870 x 649 RGB figure is calibrated on its printed axes. Nine black
experimental markers are the validation observations. The red prediction curve
is kept separate and used only to recover the thermal-age offset and initial
substrate temperature omitted from the text. Read-off bounds are +/-1 s and
+/-6e-6 m/s. Figure 9 is excluded: it describes another run and the paper does
not publish the initial temperature and clock mapping needed to combine it with
Figure 11.

## Stage C: Dienhart 1995 Figures 5.24 and 5.25

Source: J. Dienhart, *Tiefkalte Flussiggas-Lachen*, JUEL-3155 (1995),
persistent identifier http://hdl.handle.net/2128/21550. The full report is
openly downloadable from Forschungszentrum Julich.

Discrete 0.1 m thermocouple-front times are manually transcribed with the
report's +/-1.2 s timing and asymmetric radius uncertainty. Trials 3 (water)
and 5 (aluminium) calibrate one surface coefficient each. Those coefficients
are frozen for Trials 4 and 6. The report's continuous-film video ranges are a
second radius check. Detached rings, branches, pulses, and floes are recorded
as unresolved axisymmetric phenomena rather than silently digitised as a
smooth front.

## PRESLHY E3.4 diagnostic

The original scale and temperature histories remain a useful stress test, but
there is no measured liquid-to-ground inlet history for the repeated fills.
They are therefore reported as a conditional diagnostic, not used as the v0.2
component-validation gate. Temperature `X_Value` is interpolated onto
`Sync.Time`; scale mass remains on `Orig.Time`. The superseded row-by-row join
and its 1.173 ratio are withdrawn.

Before adding evidence, record the source, exact figure/table, observable and
SI units, extraction method, uncertainty, file hash, analyst/date, role
(calibration or holdout), and redistribution restrictions.
