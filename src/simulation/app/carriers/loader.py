"""
carriers/loader.py — Carrier profile loader and data models.

@file   loader.py
@brief  Loads Rogers/Bell/Telus carrier configuration from TOML files.
@detail The simulation engine reads these profiles to determine realistic
        latency distributions and error injection rates per carrier.
        Adding a new carrier requires only a new TOML file — no code changes.

@usage  registry = CarrierRegistry(config_dir="config/carriers")
        profile = registry.get("rogers")
        detected = registry.auto_detect("+14165550100")

@note   Profile values are simulation parameters derived from 3GPP/IMS
        network behavior knowledge — not certified by the actual carriers.
"""

import tomllib
import os
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache


@dataclass
class LatencyProfile:
    """
    @brief  P-percentile latency anchors in milliseconds for a carrier.
    @detail Used by SimulationEngine._sample_latency() for linear
            interpolation between percentile anchors.
    @field  p50   Median latency — 50% of requests complete within this time.
    @field  p75   75th percentile latency.
    @field  p95   95th percentile — tail latency starts here.
    @field  p99   99th percentile — rare slow requests.
    @field  p999  99.9th percentile — worst-case realistic bound.
    """

    p50: float
    p75: float
    p95: float
    p99: float
    p999: float


@dataclass
class ErrorProfile:
    """
    @brief  Per-error-type injection probabilities for a carrier.
    @detail Each probability is in range 0.0–1.0. The engine checks
            them in order: timeout > service_unavailable > invalid_token
            > roaming. First match wins (errors are mutually exclusive).
    """

    timeout_probability: float
    service_unavailable_probability: float
    invalid_token_probability: float
    roaming_not_supported_probability: float


@dataclass
class CarrierProfile:
    """
    @brief  Complete simulation profile for one Canadian carrier.
    @detail Loaded from a TOML file in config/carriers/. Contains all
            parameters needed to simulate realistic carrier behavior:
            latency distribution, error rates, supported features,
            and SIM swap detection characteristics.
    """

    name: str
    display_name: str
    mcc: str
    mnc: str
    msisdn_prefixes: list[str]
    latency_ms: LatencyProfile
    error_profiles: ErrorProfile
    sim_swap_supported: bool
    device_location_supported: bool
    number_verification_supported: bool
    sim_swap_detection_delay_hours: int
    sim_swap_max_lookback_days: int


@dataclass
class CarrierError:
    """
    @brief  A CAMARA-spec error to return instead of a success response.
    @detail Maps to CAMARA Problem Details (RFC 7807). The code field
            corresponds to CAMARA error identifiers from the OpenAPI spec.
    @field  code     CAMARA error code (e.g. "TIMEOUT", "SERVICE_UNAVAILABLE").
    @field  message  Human-readable error description.
    """

    code: str
    message: str


class CarrierRegistry:
    """
    @brief  Loads all carrier profiles from config/carriers/*.toml at startup.
    @detail Provides lookup by name and auto-detection from MSISDN prefix.
            Thread-safe after construction (read-only after _load_all).

    @usage  registry = CarrierRegistry()
            profile = registry.get("rogers")
            names = registry.list_names()
    """

    def __init__(self, config_dir: str = "config/carriers"):
        """
        @brief  Initialize registry by loading all TOML carrier profiles.
        @param  config_dir  Path to directory containing *.toml carrier files.
        @raises FileNotFoundError  If config_dir does not exist.
        @raises ValueError         If no .toml files found in config_dir.
        """
        self._profiles: dict[str, CarrierProfile] = {}
        self._load_all(config_dir)

    def _load_all(self, config_dir: str) -> None:
        """
        @brief  Scan config_dir for .toml files and parse each as a carrier.
        @param  config_dir  Directory path containing carrier TOML configs.
        @raises FileNotFoundError  If directory does not exist.
        @raises ValueError         If directory contains no TOML files.
        """
        if not os.path.exists(config_dir):
            raise FileNotFoundError(
                f"Carrier config directory not found: {config_dir}"
            )

        for filename in os.listdir(config_dir):
            if not filename.endswith(".toml"):
                continue
            path = os.path.join(config_dir, filename)
            name = filename.replace(".toml", "").lower()
            self._profiles[name] = self._parse(path, name)

        if not self._profiles:
            raise ValueError(f"No carrier profiles found in {config_dir}")

    def _parse(self, path: str, name: str) -> CarrierProfile:
        """
        @brief   Parse one TOML file into a typed CarrierProfile.
        @param   path  Absolute or relative path to the .toml file.
        @param   name  Lowercase carrier name (derived from filename).
        @return  Fully populated CarrierProfile dataclass.
        @note    Missing optional fields (p75, p999, sim_swap) use defaults.
        """
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        lat = raw["latency_ms"]
        err = raw["error_profiles"]
        feat = raw["features"]
        sim = raw.get("sim_swap", {})

        return CarrierProfile(
            name=name,
            display_name=raw["carrier"]["name"],
            mcc=raw["carrier"]["mcc"],
            mnc=raw["carrier"]["mnc"],
            msisdn_prefixes=raw["carrier"]["msisdn_prefixes"],
            latency_ms=LatencyProfile(
                p50=lat["p50"],
                p75=lat.get("p75", lat["p50"]),
                p95=lat["p95"],
                p99=lat["p99"],
                p999=lat.get("p999", lat["p99"] * 2.5),
            ),
            error_profiles=ErrorProfile(
                timeout_probability=err["timeout_probability"],
                service_unavailable_probability=err[
                    "service_unavailable_probability"
                ],
                invalid_token_probability=err["invalid_token_probability"],
                roaming_not_supported_probability=err[
                    "roaming_not_supported_probability"
                ],
            ),
            sim_swap_supported=feat["sim_swap_supported"],
            device_location_supported=feat["device_location_supported"],
            number_verification_supported=feat["number_verification_supported"],
            sim_swap_detection_delay_hours=sim.get("detection_delay_hours", 2),
            sim_swap_max_lookback_days=sim.get("max_lookback_days", 90),
        )

    def get(self, name: str) -> CarrierProfile:
        """
        @brief   Return the profile for the named carrier.
        @param   name  Carrier name (case-insensitive). e.g. "rogers".
        @return  CarrierProfile for the requested carrier.
        @raises  KeyError  If the carrier is not registered.
        @note    Use auto_detect(msisdn) to resolve carrier from a phone number.
        """
        name = name.lower()
        if name not in self._profiles:
            raise KeyError(
                f"Carrier '{name}' not found. Available: {self.list_names()}"
            )
        return self._profiles[name]

    def auto_detect(self, msisdn: str) -> CarrierProfile:
        """
        @brief   Resolve a carrier from an E.164 phone number prefix.
        @param   msisdn  Phone number in E.164 format (e.g. "+14165550100").
        @return  CarrierProfile matching the MSISDN prefix.
        @note    Falls back to Rogers if no prefix matches — reflects
                 Rogers' dominant Canadian market share (~33%).
        """
        digits = msisdn.lstrip("+")
        for profile in self._profiles.values():
            for prefix in profile.msisdn_prefixes:
                clean_prefix = prefix.replace("-", "").replace(" ", "")
                if digits.startswith(clean_prefix):
                    return profile
        return self._profiles.get("rogers") or next(
            iter(self._profiles.values())
        )

    def list_names(self) -> list[str]:
        """
        @brief   Return sorted list of all registered carrier names.
        @return  List of lowercase carrier name strings.
        """
        return sorted(self._profiles.keys())


# Module-level singleton — loaded once at startup
_registry: Optional[CarrierRegistry] = None


def get_registry() -> CarrierRegistry:
    """
    @brief   Return the module-level carrier registry singleton.
    @detail  Loads from config/carriers/ on first call. Subsequent calls
             return the cached instance.
    @return  CarrierRegistry with all carrier profiles loaded.
    """
    global _registry
    if _registry is None:
        _registry = CarrierRegistry()
    return _registry
