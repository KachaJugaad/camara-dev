"""
carriers — Carrier profile data models and TOML loader.

@brief  Loads Rogers/Bell/Telus carrier configs from TOML files and
        provides typed access via CarrierRegistry.
@detail Adding a new carrier requires only a new TOML file in
        config/carriers/ — no code changes needed.

@usage  from carriers import get_registry
        registry = get_registry()
        rogers = registry.get("rogers")
"""

from carriers.loader import (
    CarrierProfile,
    CarrierError,
    CarrierRegistry,
    LatencyProfile,
    ErrorProfile,
    get_registry,
)

__all__ = [
    "CarrierProfile",
    "CarrierError",
    "CarrierRegistry",
    "LatencyProfile",
    "ErrorProfile",
    "get_registry",
]
