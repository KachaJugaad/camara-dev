"""
engine.py — Core CAMARA simulation engine.

@file   engine.py
@brief  Apply a carrier's latency and error profile to any simulated API call.
@detail Injects realistic Canadian network behavior (Rogers/Bell/Telus)
        without a real carrier connection. All randomness is seeded for
        determinism in tests (seed=42).

@usage  engine = SimulationEngine(profile=rogers_profile, seed=42)
        result = await engine.run(surface="sim_swap", payload={...})

@note   Responses represent simulation data, not real network telemetry.
        The engine guarantees latency within the carrier's p999 bound.
"""

import asyncio
import random
from dataclasses import dataclass
from typing import Optional

from carriers import CarrierProfile, CarrierError


@dataclass
class SimResult:
    """
    @brief  Outcome of one simulated CAMARA API call.
    @detail Encapsulates success/error state, response data, carrier info,
            and the actual latency applied.

    @field  success        True if no error was injected.
    @field  data           CAMARA-spec response body (empty dict on error).
    @field  error_code     CAMARA error identifier, or None on success.
    @field  error_message  Human-readable error description, or None.
    @field  carrier        Name of the carrier profile used.
    @field  latency_ms     Actual sleep applied in milliseconds.
    @field  simulated      Always True — marks this as simulation output.
    """

    success: bool
    data: dict
    error_code: Optional[str]
    error_message: Optional[str]
    carrier: str
    latency_ms: float
    simulated: bool = True


class SimulationEngine:
    """
    @brief  Apply a carrier profile to produce a realistic CAMARA response.
    @detail Applies latency injection (always) then probabilistic error
            injection. Error injection order: timeout > service_unavailable
            > invalid_token > roaming. First match wins — realistic because
            network errors are mutually exclusive.

    @usage  engine = SimulationEngine(profile=rogers, seed=42)
            result = await engine.run("sim_swap", {"phoneNumber": "+1416..."})
    """

    def __init__(self, profile: CarrierProfile, seed: Optional[int] = None):
        """
        @brief  Create a simulation engine bound to one carrier profile.
        @param  profile  CarrierProfile loaded from TOML config.
        @param  seed     RNG seed for deterministic tests (None = random).
        """
        self.profile = profile
        self._rng = random.Random(seed)

    async def run(self, surface: str, payload: dict) -> SimResult:
        """
        @brief   Simulate one CAMARA API call against this carrier's profile.
        @param   surface  Surface name: "sim_swap", "number_verify", or
                          "device_location".
        @param   payload  Request body dict (already validated by caller).
        @return  SimResult with success/error state and response data.
        @note    Latency is always applied (via asyncio.sleep). Error
                 injection is probabilistic per carrier error_profiles.
        """
        latency = self._sample_latency()
        await asyncio.sleep(latency / 1000)

        error = self._maybe_inject_error()
        if error:
            return SimResult(
                success=False,
                data={},
                error_code=error.code,
                error_message=error.message,
                carrier=self.profile.name,
                latency_ms=latency,
            )

        data = self._build_response(surface, payload)
        return SimResult(
            success=True,
            data=data,
            error_code=None,
            error_message=None,
            carrier=self.profile.name,
            latency_ms=latency,
        )

    def _sample_latency(self) -> float:
        """
        @brief   Sample a latency value from the carrier's distribution.
        @detail  Uses linear interpolation between percentile anchors
                 (p50, p95, p99, p999). The RNG determines which
                 percentile band the sample falls into.
        @return  Latency in milliseconds (float).
        """
        p = self._rng.random()
        lat = self.profile.latency_ms
        if p < 0.50:
            return self._lerp(0, 0.50, 0, lat.p50, p)
        elif p < 0.95:
            return self._lerp(0.50, 0.95, lat.p50, lat.p95, p)
        elif p < 0.99:
            return self._lerp(0.95, 0.99, lat.p95, lat.p99, p)
        else:
            return self._lerp(0.99, 1.0, lat.p99, lat.p999, p)

    def _maybe_inject_error(self) -> Optional[CarrierError]:
        """
        @brief   Probabilistically inject a CAMARA error based on carrier
                 error rates.
        @detail  Checks error types in priority order. First matching
                 probability wins. Returns None for the happy path (~90%).
        @return  CarrierError to inject, or None if no error.
        """
        ep = self.profile.error_profiles
        checks = [
            (
                ep.timeout_probability,
                CarrierError("TIMEOUT", "Network timeout — carrier IMS unreachable"),
            ),
            (
                ep.service_unavailable_probability,
                CarrierError(
                    "SERVICE_UNAVAILABLE",
                    "Carrier service temporarily unavailable",
                ),
            ),
            (
                ep.invalid_token_probability,
                CarrierError(
                    "UNAUTHENTICATED",
                    "Token expired or invalidated by carrier cache",
                ),
            ),
            (
                ep.roaming_not_supported_probability,
                CarrierError(
                    "NOT_SUPPORTED",
                    "Device is roaming — feature unavailable on this carrier",
                ),
            ),
        ]
        for probability, error in checks:
            if self._rng.random() < probability:
                return error
        return None

    def _build_response(self, surface: str, payload: dict) -> dict:
        """
        @brief   Build a CAMARA-spec response body for the given surface.
        @param   surface  One of: "sim_swap", "number_verify", "device_location".
        @param   payload  Validated request body.
        @return  Dict containing CAMARA-compliant response fields.
        @raises  ValueError  If surface name is unknown.
        @note    Delegates to surface-specific build_response() functions.
        """
        from surfaces import sim_swap, number_verify, location_verification

        builders = {
            "sim_swap": sim_swap.build_response,
            "sim_swap_check": sim_swap.build_check_response,
            "number_verify": number_verify.build_response,
            "location_verification": location_verification.build_response,
        }
        builder = builders.get(surface)
        if not builder:
            raise ValueError(f"Unknown surface: {surface}")
        return builder(payload, self._rng, self.profile)

    @staticmethod
    def _lerp(x0: float, x1: float, y0: float, y1: float, x: float) -> float:
        """
        @brief   Linear interpolation between two points.
        @param   x0  Lower x bound.
        @param   x1  Upper x bound.
        @param   y0  y value at x0.
        @param   y1  y value at x1.
        @param   x   Point to interpolate at (x0 <= x <= x1).
        @return  Interpolated y value.
        @note    Used internally for latency sampling between percentiles.
        """
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
