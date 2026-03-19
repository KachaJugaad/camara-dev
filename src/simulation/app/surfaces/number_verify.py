"""
surfaces/number_verify.py — CAMARA Number Verification surface.

@file   number_verify.py
@brief  UC2 — Phone number verification for login and identity.
@detail Verifies that the phone number a user typed matches the SIM card
        in their device. Used for passwordless login, account recovery,
        and identity proofing.

@spec   CAMARA NumberVerification — Fall25 v1
        github.com/camaraproject/NumberVerification
@endpoint POST /number-verification/v1/verify

@note   Response always contains 'devicePhoneNumberVerified' (bool).
        This does NOT constitute legal identity verification.
"""

import random
from typing import Any


# 92% match rate — realistic for genuine users
_VERIFICATION_SUCCESS_RATE = 0.92

# Failure reason weights when verification fails
_FAILURE_REASONS = [
    ("NUMBER_MISMATCH", 0.6),
    ("NUMBER_PORTED", 0.2),
    ("DEVICE_NOT_APPLICABLE", 0.2),
]


def build_response(payload: dict, rng: random.Random, carrier: Any) -> dict:
    """
    @brief   Build a CAMARA Number Verification verify response.
    @param   payload  Validated request body with phoneNumber.
    @param   rng      Seeded Random instance for deterministic simulation.
    @param   carrier  CarrierProfile (used for carrier-specific behavior).
    @return  Dict with "devicePhoneNumberVerified" (bool) and optional
             "verificationFailureReason" on failure.
    @detail  Verification succeeds ~92% of the time (realistic for genuine
             users). The 8% failure rate covers: typos, ported numbers,
             VoIP numbers, and device changes.
    """
    verified = rng.random() < _VERIFICATION_SUCCESS_RATE

    response: dict = {
        "devicePhoneNumberVerified": verified,
    }

    if not verified:
        reasons = [r for r, _ in _FAILURE_REASONS]
        weights = [w for _, w in _FAILURE_REASONS]
        response["verificationFailureReason"] = rng.choices(reasons, weights=weights)[0]

    return response


def validate_request(payload: dict) -> list[str]:
    """
    @brief   Validate a number verification request against CAMARA spec.
    @param   payload  Raw request body dict.
    @return  List of validation error messages. Empty list means valid.
    @detail  Checks:
             - phoneNumber is present and in E.164 format (starts with +).
             - phoneNumber length is 10–16 chars (E.164 range).
    """
    errors = []

    phone = payload.get("phoneNumber", "")
    if not phone:
        errors.append("phoneNumber is required")
    elif not phone.startswith("+"):
        errors.append("phoneNumber must be in E.164 format (e.g. +14165550100)")
    elif len(phone) < 10 or len(phone) > 16:
        errors.append("phoneNumber length invalid for E.164 format")

    return errors
