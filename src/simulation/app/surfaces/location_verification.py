"""
surfaces/location_verification.py — CAMARA Location Verification surface.

@file   location_verification.py
@brief  UC3 — Device location verification for fraud detection and logistics.
@detail Verifies whether a device is within a specified geographic area.
        Renamed from device_location per CAMARA Commonalities Design Guide:
        "for Device Location Verification API, api-name is location-verification"

@spec   CAMARA DeviceLocation — location-verification.yaml
        github.com/camaraproject/DeviceLocation
@endpoint POST /location-verification/v1/verify

@note   verificationResult enum: TRUE/FALSE/PARTIAL (no UNKNOWN per spec).
        matchRate is integer 1-99 (not float), only for PARTIAL results.
        maxAge is in seconds (integer, min 0).
"""

import random
from datetime import datetime, timezone
from typing import Any


# CAMARA location-verification.yaml: VerificationResult enum
# NOTE: Spec defines only THREE values — no UNKNOWN
RESULT_TRUE = "TRUE"
RESULT_FALSE = "FALSE"
RESULT_PARTIAL = "PARTIAL"

# Result distribution reflecting real network behavior
# Adjusted from original: UNKNOWN removed per spec, probability redistributed
_RESULT_WEIGHTS = [
    (RESULT_TRUE, 0.82),
    (RESULT_FALSE, 0.12),
    (RESULT_PARTIAL, 0.06),
]

# Probability of UNABLE_TO_FULFILL_MAX_AGE when maxAge=0
_FRESH_LOCATION_FAILURE_RATE = 0.05


def build_response(payload: dict, rng: random.Random, carrier: Any) -> dict:
    """
    @brief   Build a CAMARA Location Verification verify response.
    @param   payload  Validated request body with device.phoneNumber and area.
    @param   rng      Seeded Random instance for deterministic simulation.
    @param   carrier  CarrierProfile (used for carrier-specific behavior).
    @return  Dict with verificationResult (enum), lastLocationTime (RFC3339),
             and optional matchRate (integer 1-99 for PARTIAL only).
    @spec    location-verification.yaml: VerifyLocationResponse —
             verificationResult and lastLocationTime are required.
             matchRate is integer 1-99, included only for PARTIAL.
    """
    results = [r for r, _ in _RESULT_WEIGHTS]
    weights = [w for _, w in _RESULT_WEIGHTS]

    verification_result = rng.choices(results, weights=weights)[0]

    # location-verification.yaml: lastLocationTime is required in response
    last_location_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    response: dict = {
        "verificationResult": verification_result,
        "lastLocationTime": last_location_time,
    }

    # location-verification.yaml: matchRate integer 1-99, only for PARTIAL
    if verification_result == RESULT_PARTIAL:
        match_rate = rng.randint(1, 99)
        response["matchRate"] = match_rate

    return response


def validate_request(payload: dict) -> list[str]:
    """
    @brief   Validate a location verification request against CAMARA spec.
    @param   payload  Raw request body dict.
    @return  List of validation error messages. Empty list means valid.
    @spec    location-verification.yaml: VerifyLocationRequest —
             area is required, device is optional (3-legged flow).
             maxAge is integer in seconds, minimum 0.
    """
    errors = []

    device = payload.get("device", {})
    phone = device.get("phoneNumber", "")
    if device and phone:
        if not phone.startswith("+"):
            errors.append("device.phoneNumber must be E.164 format")

    area = payload.get("area", {})
    if not area:
        # location-verification.yaml: area is required
        errors.append("area is required")
    else:
        area_type = area.get("areaType")
        if area_type not in ("CIRCLE",):
            errors.append("area.areaType must be 'CIRCLE'")

        center = area.get("center", {})
        if "latitude" not in center or "longitude" not in center:
            errors.append("area.center must contain latitude and longitude")
        else:
            lat = center.get("latitude", 0)
            lng = center.get("longitude", 0)
            if not (-90 <= lat <= 90):
                errors.append("area.center.latitude must be between -90 and 90")
            if not (-180 <= lng <= 180):
                errors.append("area.center.longitude must be between -180 and 180")

        radius = area.get("radius")
        if radius is None:
            errors.append("area.radius is required (meters)")
        elif not isinstance(radius, (int, float)) or radius <= 0:
            errors.append("area.radius must be a positive number (meters)")
        elif radius > 200000:
            errors.append("area.radius cannot exceed 200000 meters")

    # location-verification.yaml: maxAge is integer, minimum 0, in seconds
    max_age = payload.get("maxAge")
    if max_age is not None:
        if not isinstance(max_age, int) or max_age < 0:
            errors.append("maxAge must be a non-negative integer (seconds)")

    return errors


def check_max_age_fulfillable(payload: dict, rng: random.Random) -> bool:
    """
    @brief   Check if maxAge=0 (fresh location) can be fulfilled.
    @param   payload  Request body with optional maxAge.
    @param   rng      Seeded Random for deterministic simulation.
    @return  True if fulfillable, False if should return 422 error.
    @spec    location-verification.yaml: error 422
             LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE
    """
    max_age = payload.get("maxAge")
    if max_age == 0:
        return rng.random() >= _FRESH_LOCATION_FAILURE_RATE
    return True
