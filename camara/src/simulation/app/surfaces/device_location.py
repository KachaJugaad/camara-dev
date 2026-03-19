"""
surfaces/device_location.py — CAMARA Device Location Verification surface.

@file   device_location.py
@brief  UC3 — Device location for fraud detection and logistics.
@detail Verifies whether a device is within a specified geographic area.
        Used by e-commerce to check if a user's device matches their claimed
        shipping address, and by logistics to confirm driver location.

@spec   CAMARA DeviceLocation — Spring25 v0.2.0
        github.com/camaraproject/DeviceLocation
@endpoint POST /device-location/v0/verify

@note   Response always contains 'verificationResult' (enum string).
        Location is cell-tower resolution (city-level ±5km), not GPS-level.
"""

import random
from typing import Any


# CAMARA spec verification result enum values
RESULT_TRUE = "TRUE"
RESULT_FALSE = "FALSE"
RESULT_UNKNOWN = "UNKNOWN"
RESULT_PARTIAL = "PARTIAL"

# Result distribution reflecting real network behavior
_RESULT_WEIGHTS = [
    (RESULT_TRUE, 0.78),
    (RESULT_FALSE, 0.12),
    (RESULT_UNKNOWN, 0.07),
    (RESULT_PARTIAL, 0.03),
]


def build_response(payload: dict, rng: random.Random, carrier: Any) -> dict:
    """
    @brief   Build a CAMARA Device Location verify response.
    @param   payload  Validated request body with device.phoneNumber and area.
    @param   rng      Seeded Random instance for deterministic simulation.
    @param   carrier  CarrierProfile (used for carrier-specific behavior).
    @return  Dict with "verificationResult" (enum) and optional "matchRate".
    @detail  Result distribution:
             - 78% TRUE   (device where user claims — legitimate users)
             - 12% FALSE  (device not in area — potential fraud signal)
             -  7% UNKNOWN (carrier can't resolve — device off-network)
             -  3% PARTIAL (boundary case — device on edge of area)
             matchRate (0.0–1.0) included for TRUE and PARTIAL results.
    """
    results = [r for r, _ in _RESULT_WEIGHTS]
    weights = [w for _, w in _RESULT_WEIGHTS]

    verification_result = rng.choices(results, weights=weights)[0]

    response: dict = {
        "verificationResult": verification_result,
    }

    if verification_result in (RESULT_TRUE, RESULT_PARTIAL):
        if verification_result == RESULT_TRUE:
            match_rate = rng.uniform(0.75, 1.0)
        else:
            match_rate = rng.uniform(0.4, 0.75)
        response["matchRate"] = round(match_rate, 2)

    return response


def validate_request(payload: dict) -> list[str]:
    """
    @brief   Validate a device location request against CAMARA spec.
    @param   payload  Raw request body dict.
    @return  List of validation error messages. Empty list means valid.
    @detail  Checks:
             - device.phoneNumber is present and E.164 format.
             - area is present with areaType "CIRCLE" (only type in v0.2).
             - area.center has valid latitude (-90..90) and longitude (-180..180).
             - area.radius is positive and <= 200,000 meters (200km max).
    """
    errors = []

    device = payload.get("device", {})
    phone = device.get("phoneNumber", "")
    if not phone:
        errors.append("device.phoneNumber is required")
    elif not phone.startswith("+"):
        errors.append("device.phoneNumber must be E.164 format")

    area = payload.get("area", {})
    if not area:
        errors.append("area is required")
    else:
        area_type = area.get("areaType")
        if area_type not in ("CIRCLE",):
            errors.append("area.areaType must be 'CIRCLE' (only type in v0.2)")

        center = area.get("center", {})
        if "latitude" not in center or "longitude" not in center:
            errors.append("area.center must contain latitude and longitude")
        else:
            lat = center.get("latitude", 0)
            lng = center.get("longitude", 0)
            if not (-90 <= lat <= 90):
                errors.append(
                    "area.center.latitude must be between -90 and 90"
                )
            if not (-180 <= lng <= 180):
                errors.append(
                    "area.center.longitude must be between -180 and 180"
                )

        radius = area.get("radius")
        if radius is None:
            errors.append("area.radius is required (meters)")
        elif not isinstance(radius, (int, float)) or radius <= 0:
            errors.append("area.radius must be a positive number (meters)")
        elif radius > 200000:
            errors.append("area.radius cannot exceed 200000 meters")

    return errors
