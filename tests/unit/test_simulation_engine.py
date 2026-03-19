"""
tests/unit/test_simulation_engine.py — Unit tests for the simulation engine.

@file   test_simulation_engine.py
@brief  Tests carrier loading, latency sampling, error injection, surface
        validation, and auth token handling. Updated for CAMARA Fall25 spec.
@detail All tests use seed=42 for deterministic behavior.

@usage  pytest tests/unit/ -v
"""

import pytest
import random

from engine import SimulationEngine


# ── Carrier registry tests ────────────────────────────────────────────────────


def test_all_three_carriers_load(carrier_registry):
    """
    @brief  All three Canadian carriers must be present in the registry.
    @verify Rogers, Bell, and Telus are loaded from config/carriers/.
    """
    names = carrier_registry.list_names()
    assert "rogers" in names
    assert "bell" in names
    assert "telus" in names


def test_carrier_has_required_fields(rogers):
    """
    @brief  A carrier profile must have all required simulation fields.
    """
    assert rogers.name == "rogers"
    assert rogers.display_name == "Rogers"
    assert rogers.latency_ms.p50 > 0
    assert rogers.latency_ms.p95 > rogers.latency_ms.p50
    assert rogers.latency_ms.p99 > rogers.latency_ms.p95
    assert 0.0 <= rogers.error_profiles.timeout_probability <= 1.0


def test_auto_detect_toronto_number_is_rogers(carrier_registry):
    """@brief A Toronto +1416 MSISDN should resolve to Rogers."""
    profile = carrier_registry.auto_detect("+14165550100")
    assert profile.name == "rogers"


def test_auto_detect_vancouver_number_is_telus(carrier_registry):
    """@brief A Vancouver +1604 MSISDN should resolve to Telus."""
    profile = carrier_registry.auto_detect("+16045550100")
    assert profile.name == "telus"


def test_auto_detect_unknown_falls_back_to_rogers(carrier_registry):
    """@brief An unrecognized prefix should fall back to Rogers."""
    profile = carrier_registry.auto_detect("+19995550100")
    assert profile.name == "rogers"


# ── Latency tests ─────────────────────────────────────────────────────────────


def test_rogers_latency_within_p99_bound(rogers):
    """@brief Over 1000 samples, Rogers p99 must stay within realistic bounds."""
    engine = SimulationEngine(profile=rogers, seed=42)
    latencies = [engine._sample_latency() for _ in range(1000)]
    latencies.sort()
    p99_actual = latencies[989]
    assert p99_actual < rogers.latency_ms.p99 * 2.5


def test_telus_faster_than_bell_p50(carrier_registry):
    """@brief Telus p50 should be lower than Bell p50 per carrier profiles."""
    assert (
        carrier_registry.get("telus").latency_ms.p50
        < carrier_registry.get("bell").latency_ms.p50
    )


# ── Error injection tests ─────────────────────────────────────────────────────


def test_rogers_timeout_rate_in_expected_range(rogers):
    """@brief Rogers timeout rate with seed=42 must be between 3% and 7%."""
    engine = SimulationEngine(profile=rogers, seed=42)
    timeout_count = sum(
        1
        for _ in range(2000)
        if (err := engine._maybe_inject_error()) and err.code == "TIMEOUT"
    )
    rate = timeout_count / 2000
    assert 0.03 <= rate <= 0.07


def test_no_error_injected_on_most_requests(rogers):
    """@brief Most requests (>80%) should succeed without error injection."""
    engine = SimulationEngine(profile=rogers, seed=42)
    errors = sum(1 for _ in range(1000) if engine._maybe_inject_error() is not None)
    assert errors < 150


# ── SIM swap surface tests ────────────────────────────────────────────────────


def test_sim_swap_validate_rejects_missing_phone():
    """@brief SIM swap request without phoneNumber must fail validation."""
    from surfaces.sim_swap import validate_request

    errors = validate_request({})
    assert any("phoneNumber" in e for e in errors)


def test_sim_swap_validate_rejects_non_e164():
    """@brief Phone number without + prefix must fail E.164 validation."""
    from surfaces.sim_swap import validate_request

    errors = validate_request({"phoneNumber": "14165550100"})
    assert any("E.164" in e for e in errors)


def test_sim_swap_check_validate_rejects_max_age_over_2400():
    """
    @brief  maxAge > 2400 must be rejected per CAMARA spec.
    @spec   sim-swap.yaml: CreateCheckSimSwap maxAge maximum is 2400.
    """
    from surfaces.sim_swap import validate_check_request

    errors = validate_check_request({"phoneNumber": "+14165550100", "maxAge": 9999})
    assert any("2400" in e for e in errors)


def test_sim_swap_valid_request_passes():
    """@brief A well-formed SIM swap request must pass validation."""
    from surfaces.sim_swap import validate_request

    errors = validate_request({"phoneNumber": "+14165550100"})
    assert errors == []


@pytest.mark.asyncio
async def test_sim_swap_response_has_required_field(rogers):
    """
    @brief  SIM swap response must contain latestSimChange.
    @spec   sim-swap.yaml: SimSwapInfo — latestSimChange required, nullable.
    """
    from surfaces.sim_swap import build_response

    rng = random.Random(42)
    result = build_response({"phoneNumber": "+14165550100"}, rng, rogers)
    assert "latestSimChange" in result


def test_sim_swap_check_response_has_swapped_field(rogers):
    """
    @brief  SIM swap /check response must contain swapped (boolean).
    @spec   sim-swap.yaml: CheckSimSwapInfo — swapped is required boolean.
    """
    from surfaces.sim_swap import build_check_response

    rng = random.Random(42)
    result = build_check_response(
        {"phoneNumber": "+14165550100", "maxAge": 240}, rng, rogers
    )
    assert "swapped" in result
    assert isinstance(result["swapped"], bool)


# ── Number verification surface tests ────────────────────────────────────────


def test_number_verify_validate_rejects_missing_phone():
    """@brief Number verify without phoneNumber must fail validation."""
    from surfaces.number_verify import validate_request

    errors = validate_request({})
    assert any("phoneNumber" in e for e in errors)


def test_number_verify_response_has_verified_field(rogers):
    """
    @brief  Number verify response must contain devicePhoneNumberVerified.
    @spec   number-verification.yaml: NumberVerificationMatchResponse.
    """
    from surfaces.number_verify import build_response

    result = build_response({"phoneNumber": "+14165550100"}, random.Random(42), rogers)
    assert "devicePhoneNumberVerified" in result
    assert isinstance(result["devicePhoneNumberVerified"], bool)


# ── Location verification surface tests ───────────────────────────────────────


def test_location_verification_validate_rejects_missing_area():
    """
    @brief  Location verification without area must fail validation.
    @spec   location-verification.yaml: area is required.
    """
    from surfaces.location_verification import validate_request

    errors = validate_request({"device": {"phoneNumber": "+14165550100"}})
    assert any("area" in e for e in errors)


def test_location_verification_validate_rejects_invalid_coords():
    """@brief Latitude outside -90..90 must fail validation."""
    from surfaces.location_verification import validate_request

    errors = validate_request(
        {
            "device": {"phoneNumber": "+14165550100"},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": 200, "longitude": -79.38},
                "radius": 5000,
            },
        }
    )
    assert any("latitude" in e for e in errors)


def test_location_verification_result_enum_values(rogers):
    """
    @brief  verificationResult must be one of TRUE/FALSE/PARTIAL (no UNKNOWN).
    @spec   location-verification.yaml: VerificationResult enum.
    """
    from surfaces.location_verification import (
        build_response,
        RESULT_TRUE,
        RESULT_FALSE,
        RESULT_PARTIAL,
    )

    payload = {
        "device": {"phoneNumber": "+14165550100"},
        "area": {
            "areaType": "CIRCLE",
            "center": {"latitude": 43.65, "longitude": -79.38},
            "radius": 5000,
        },
    }
    result = build_response(payload, random.Random(42), rogers)
    assert result["verificationResult"] in (
        RESULT_TRUE,
        RESULT_FALSE,
        RESULT_PARTIAL,
    )


def test_location_verification_match_rate_is_integer(rogers):
    """
    @brief  matchRate must be integer 1-99, not float.
    @spec   location-verification.yaml: MatchRate integer min=1 max=99.
    """
    from surfaces.location_verification import build_response, RESULT_PARTIAL

    # Run enough times to get a PARTIAL result
    for seed in range(100):
        result = build_response(
            {
                "device": {"phoneNumber": "+14165550100"},
                "area": {
                    "areaType": "CIRCLE",
                    "center": {"latitude": 43.65, "longitude": -79.38},
                    "radius": 5000,
                },
            },
            random.Random(seed),
            rogers,
        )
        if result["verificationResult"] == RESULT_PARTIAL:
            assert isinstance(result["matchRate"], int)
            assert 1 <= result["matchRate"] <= 99
            return
    pytest.skip("No PARTIAL result generated in 100 seeds")


def test_location_verification_response_has_last_location_time(rogers):
    """
    @brief  Response must contain lastLocationTime (RFC3339).
    @spec   location-verification.yaml: VerifyLocationResponse —
            lastLocationTime is required.
    """
    from surfaces.location_verification import build_response

    result = build_response(
        {
            "device": {"phoneNumber": "+14165550100"},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": 43.65, "longitude": -79.38},
                "radius": 5000,
            },
        },
        random.Random(42),
        rogers,
    )
    assert "lastLocationTime" in result
    assert isinstance(result["lastLocationTime"], str)


# ── Auth tests ────────────────────────────────────────────────────────────────


def test_validate_bearer_rejects_missing_header():
    """@brief Missing Authorization header must raise 401."""
    from auth import validate_bearer
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        validate_bearer(None)
    assert exc.value.status_code == 401


def test_auth_error_uses_camara_error_info_schema():
    """
    @brief  Auth 401 error must use CAMARA ErrorInfo schema.
    @spec   CAMARA_common.yaml: ErrorInfo — status=int, code=str, message=str.
    """
    from auth import validate_bearer
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        validate_bearer(None)
    detail = exc.value.detail
    assert isinstance(detail["status"], int)
    assert isinstance(detail["code"], str)
    assert isinstance(detail["message"], str)
    assert detail["status"] == 401
    assert detail["code"] == "UNAUTHENTICATED"


def test_validate_bearer_accepts_demo_key():
    """@brief Demo keys must always be valid."""
    from auth import validate_bearer

    claims = validate_bearer("Bearer demo-sandbox-key-rogers")
    assert claims.carrier_override == "rogers"


def test_issue_key_is_deterministic():
    """@brief Same email always produces the same API key."""
    from auth import issue_key

    key1 = issue_key("test@example.ca")
    key2 = issue_key("test@example.ca")
    assert key1 == key2


def test_issued_key_is_valid():
    """@brief A key issued by issue_key() must pass validate_bearer()."""
    from auth import issue_key, validate_bearer

    key = issue_key("newdev@startup.ca")
    claims = validate_bearer(f"Bearer {key}")
    assert claims.email == "newdev@startup.ca"
