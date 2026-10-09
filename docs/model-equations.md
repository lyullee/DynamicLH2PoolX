# Model equations and code map

Both packages calculate a pool evaporation source, not atmospheric dispersion.
The post-shutoff study begins with liquid already reaching a horizontal surface.

## LH2PoolX

`pool.py` evaluates CoolProp saturated hydrogen properties. For a saturated storage
liquid it computes an isenthalpic flash fraction x, clipped to [0,1], and an explicitly
declared ground inflow q_l=q_release(1-x)f_deposition. The substrate heat flux is
k(T0-Tsat)/sqrt(pi*alpha*t), optionally capped at 120 kW/m2; j_ev=q_heat/L_v.
For an unconstrained pool A=q_l/j_ev, R=sqrt(A/pi), and q_ev=A*j_ev=q_l.
A radius cap gives an unmet inflow rate; it does not integrate stored inventory.
The observed-footprint route uses independently supplied A and q_ev=A*j_ev.
It does not infer deposition from observations.

## DynamicLH2PoolX

`inflow.py` gives piecewise-constant declared ground inflow. `spreading.py` stores
total depth h and radial flow m on annular finite volumes. Mobile depth is
h_m=max(h-h_ret,0), m=h_m*u. Cell fluxes use the Rusanov formula with
F=(m,m*u+g'*h_m**2/2); signal speed is max(abs(u)+sqrt(g'*h_m)) across a face.
Radial face areas and the g'*h_m**2/(2*r) geometric momentum term are explicit.
After the transport update the code damps momentum by
1+dt*(C_f*abs(u)/max(h_m,h_dry)+nu/max(h_m,h_dry)**2).
This discrete damping is the implemented friction operator.

`dynamic_pool.py` applies transport, ground inflow, local wet-contact age and
evaporation in that order. Solid conduction is integrated analytically as
dh_cap=2*chi*k*(T0-Tsat)/(rho_l*L_v*sqrt(pi*alpha))*(sqrt(tau2)-sqrt(tau1)).
Water uses dh_cap=q_heat*dt/(rho_l*L_v). Actual evaporated depth is bounded by
available liquid; mass increments are summed with annular cell areas.
The default vapor momentum closure leaves organized radial liquid momentum in the
remaining mobile layer; near-dry mobile cells have zero momentum.

Wet contact age advances only in wet cells and is retained across drying and
rewetting. Lateral conduction and dry-surface reheating are not calculated.
Total inventory includes positive depths below the reporting threshold. A zero
reported radius is therefore not necessarily zero inventory.
The ledger records inflow, remaining liquid, evaporated mass, boundary escape,
signed numerical mass adjustment and unledgered residual.

The numerical methods draw on Dienhart, JUEL-3155 (1995), and finite-volume methods
described by LeVeque (2002), DOI 10.1017/CBO9780511791253. They are independently
implemented and the study specifies which physical and numerical settings are used.
The radius evidence does not directly validate post-shutoff evaporation rates.
