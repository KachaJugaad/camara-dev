"""
surfaces/sim_swap.py — CAMARA SIM Swap API surface.

@file   sim_swap.py
@brief  UC1 — SIM swap fraud detection for Canadian carriers.
@detail Implements both CAMARA SIM Swap operations:
        - /retrieve-date: returns timestamp of last SIM swap
        - /check: returns boolean whether swap occurred in period

@spec   CAMARA SimSwap — sim-swap.yaml
        github.com/camaraproject/SimSwap
@endpoints POST /sim-swap/v1/retrieve-date
           POST /sim-swap/v1/check

@note   latestSimChange is nullable per spec (sim-swap.yaml SimSwapInfo).
        maxAge maximum is 2400 hours per spec (sim-swap.yaml CreateCheckSimSwap).
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any


# Probability that a request finds a recent SIM swap (~8% realistic fraud rate)
_SWAP_PROBABILITY = 0.08

# CAMARA SimSwap sim-swap.yaml: CreateCheckSimSwap maxAge maximum is 2400
MAX_AGE_HOURS = 2400

# Canadian carrier privacy threshold — simulate OUT_OF_RANGE for >720 hours
CARRIER_PRIVACY_THRESHOLD_HOURS = 720


def build_response(payload: dict, rng: random.Random, carrier: Any) -> dict:
    """
    @brief   Build a CAMARA SIM Swap retrieve-date response (SimSwapInfo).
    @param   payload  Validated request body with phoneNumber.
    @param   rng      Seeded Random instance for deterministic simulation.
    @param   carrier  CarrierProfile with sim_swap detection parameters.
    @return  Dict with "latestSimChange" key (ISO8601 string or None).
    @detail  ~8% of requests find a recent swap (realistic fraud signal rate).
             latestSimChange is nullable per sim-swap.yaml SimSwapInfo schema.
    @spec    sim-swap.yaml: SimSwapInfo — latestSimChange is nullable datetime.
    """
    swap_occurred = rng.random() < _SWAP_PROBABILITY

    if swap_occurred:
        hours_ago = rng.uniform(
            carrier.sim_swap_detection_delay_hours,
            min(
                carrier.sim_swap_max_lookback_days * 24,
                CARRIER_PRIVACY_THRESHOLD_HOURS,
            ),
        )
        swap_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        # CAMARA spec: must follow RFC 3339 with time zone
        latest_sim_change = swap_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    else:
        # sim-swap.yaml: latestSimChange is nullable — null means no swap
        latest_sim_change = None

    return {
        "latestSimChange": latest_sim_change,
    }


def build_check_response(
    payload: dict, rng: random.Random, carrier: Any
) -> dict:
    """
    @brief   Build a CAMARA SIM Swap check response (CheckSimSwapInfo).
    @param   payload  Validated request body with phoneNumber and optional maxAge.
    @param   rng      Seeded Random instance for deterministic simulation.
    @param   carrier  CarrierProfile with sim_swap detection parameters.
    @return  Dict with "swapped" key (boolean, required, not nullable).
    @spec    sim-swap.yaml: CheckSimSwapInfo — swapped is required boolean.
    """
    max_age_hours = payload.get("maxAge", 240)
    # Swap probability scales with window size — larger window = more likely
    adjusted_prob = _SWAP_PROBABILITY * min(max_age_hours / 240, 1.0)
    swapped = rng.random() < adjusted_prob

    return {
        "swapped": swapped,
    }


def validate_request(payload: dict) -> list[str]:
    """
    @brief   Validate a SIM swap retrieve-date request against CAMARA spec.
    @param   payload  Raw request body dict.
    @return  List of validation error messages. Empty list means valid.
    @detail  For retrieve-date: phoneNumber required, no maxAge constraint.
    @spec    sim-swap.yaml: CreateSimSwapDate — only phoneNumber field.
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


def validate_check_request(payload: dict) -> list[str]:
    """
    @brief   Validate a SIM swap /check request against CAMARA spec.
    @param   payload  Raw request body dict.
    @return  List of validation error messages. Empty list means valid.
    @detail  phoneNumber optional (3-legged flow), maxAge range 1-2400.
    @spec    sim-swap.yaml: CreateCheckSimSwap — maxAge min=1 max=2400.
    """
    errors = []

    phone = payload.get("phoneNumber", "")
    if phone:
        if not phone.startswith("+"):
            errors.append(
                "phoneNumber must be in E.164 format (e.g. +14165550100)"
            )
        elif len(phone) < 10 or len(phone) > 16:
            errors.append("phoneNumber length invalid for E.164 format")

    max_age = payload.get("maxAge")
    if max_age is not None:
        if not isinstance(max_age, int) or max_age < 1:
            errors.append("maxAge must be a positive integer (hours)")
        # CAMARA SimSwap sim-swap.yaml: maxAge maximum is 2400
        elif max_age > MAX_AGE_HOURS:
            errors.append(
                f"maxAge cannot exceed {MAX_AGE_HOURS} hours "
                f"(per CAMARA SimSwap spec)"
            )

    return errors
