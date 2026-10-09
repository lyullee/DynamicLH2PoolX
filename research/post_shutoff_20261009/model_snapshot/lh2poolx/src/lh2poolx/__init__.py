"""Evidence-qualified LH2 pool source terms for dispersion-model inputs."""

from .pool import (
    CONCRETE_CRYOGENIC,
    CRITICAL_HEAT_FLUX_W_M2,
    LH2Release,
    ObservedFootprintSource,
    PoolSource,
    Substrate,
    evaluate_observed_footprint_source,
    evaluate_pool_source,
    flash_vapour_fraction,
)

__version__ = "0.1.2"

__all__ = [
    "__version__", "CONCRETE_CRYOGENIC", "CRITICAL_HEAT_FLUX_W_M2",
    "LH2Release", "PoolSource", "ObservedFootprintSource", "Substrate",
    "evaluate_pool_source", "evaluate_observed_footprint_source",
    "flash_vapour_fraction",
]
