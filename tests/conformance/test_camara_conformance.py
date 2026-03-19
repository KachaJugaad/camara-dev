"""
tests/conformance/test_camara_conformance.py — CAMARA spec conformance tests.

@file   test_camara_conformance.py
@brief  Verifies all CAMARA surfaces return spec-compliant response schemas.
@detail Tests derived from CAMARA Fall25 OpenAPI specs. If these pass, the
        sandbox endpoints match the CAMARA standard for response structure.

@usage  pytest tests/conformance/ -v
@note   Uses X-Seed=99 for deterministic success paths.
"""

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)

ROGERS_KEY = "demo-sandbox-key-rogers"
SEED_HEADERS = {"Authorization": f"Bearer {ROGERS_KEY}", "X-Seed": "99"}


# ── ErrorInfo schema conformance ─────────────────────────────────────────────


class TestErrorInfoSchema:
    """
    @brief  CAMARA ErrorInfo must have status (int), code (str), message (str).
    @spec   CAMARA_common.yaml: ErrorInfo schema — all three fields required.
    """

    def test_401_has_error_info_fields(self):
        """@brief Unauthenticated error must return full ErrorInfo."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 401
        body = r.json()
        assert isinstance(body["status"], int)
        assert isinstance(body["code"], str)
        assert isinstance(body["message"], str)

    def test_400_has_error_info_fields(self):
        """@brief Validation error must return full ErrorInfo."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers=SEED_HEADERS,
            json={},
        )
        assert r.status_code == 400
        body = r.json()
        assert isinstance(body["status"], int)
        assert isinstance(body["code"], str)
        assert isinstance(body["message"], str)
        assert body["code"] == "INVALID_ARGUMENT"


# ── SIM Swap conformance ─────────────────────────────────────────────────────


class TestSimSwapConformance:
    """
    @brief  SIM Swap responses must match sim-swap.yaml schemas.
    @spec   SimSwapInfo: latestSimChange (nullable datetime).
            CheckSimSwapInfo: swapped (required boolean).
    """

    def test_retrieve_date_schema(self):
        """@brief SimSwapInfo must have latestSimChange (str or null)."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers=SEED_HEADERS,
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "latestSimChange" in body
        val = body["latestSimChange"]
        assert val is None or isinstance(val, str)

    def test_check_schema(self):
        """@brief CheckSimSwapInfo must have swapped (bool, not nullable)."""
        r = client.post(
            "/sim-swap/v1/check",
            headers=SEED_HEADERS,
            json={"phoneNumber": "+14165550100", "maxAge": 24},
        )
        assert r.status_code == 200
        body = r.json()
        assert "swapped" in body
        assert isinstance(body["swapped"], bool)


# ── Number Verification conformance ──────────────────────────────────────────


class TestNumberVerificationConformance:
    """
    @brief  Number Verification response must match spec schema.
    @spec   NumberVerificationMatchResponse: devicePhoneNumberVerified (bool).
    """

    def test_verify_schema(self):
        """@brief Response must contain devicePhoneNumberVerified (bool)."""
        r = client.post(
            "/number-verification/v1/verify",
            headers=SEED_HEADERS,
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "devicePhoneNumberVerified" in body
        assert isinstance(body["devicePhoneNumberVerified"], bool)


# ── Location Verification conformance ────────────────────────────────────────


class TestLocationVerificationConformance:
    """
    @brief  Location Verification responses must match spec schema.
    @spec   VerifyLocationResponse: verificationResult (enum), lastLocationTime.
    """

    PAYLOAD = {
        "device": {"phoneNumber": "+14165550100"},
        "area": {
            "areaType": "CIRCLE",
            "center": {"latitude": 43.6532, "longitude": -79.3832},
            "radius": 10000,
        },
    }

    def test_verify_schema(self):
        """@brief Response must have verificationResult and lastLocationTime."""
        r = client.post(
            "/location-verification/v1/verify",
            headers=SEED_HEADERS,
            json=self.PAYLOAD,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verificationResult"] in ("TRUE", "FALSE", "PARTIAL")
        assert "lastLocationTime" in body
        assert isinstance(body["lastLocationTime"], str)

    def test_verification_result_enum_values(self):
        """
        @brief  verificationResult must only be TRUE, FALSE, or PARTIAL.
        @spec   No UNKNOWN value per Fall25 spec.
        """
        for seed in range(50):
            r = client.post(
                "/location-verification/v1/verify",
                headers={
                    "Authorization": f"Bearer {ROGERS_KEY}",
                    "X-Seed": str(seed + 1000),
                },
                json=self.PAYLOAD,
            )
            if r.status_code == 200:
                result = r.json()["verificationResult"]
                assert result in (
                    "TRUE",
                    "FALSE",
                    "PARTIAL",
                ), f"Unexpected verificationResult: {result}"


# ── Response headers conformance ─────────────────────────────────────────────


class TestResponseHeadersConformance:
    """
    @brief  Every response must include CAMARA spec headers.
    @spec   CAMARA Commonalities: x-correlator, spec version headers.
    """

    def test_spec_version_headers(self):
        """@brief X-CAMARA-Spec-Version must be present on all responses."""
        r = client.get("/health")
        assert r.headers["X-CAMARA-Spec-Version"] == "Fall25"
        assert "x-correlator" in r.headers

    def test_x_correlator_echo(self):
        """@brief Server must echo back x-correlator if provided."""
        r = client.get(
            "/health",
            headers={"x-correlator": "test-correlation-id-123"},
        )
        assert r.headers["x-correlator"] == "test-correlation-id-123"

    def test_simulation_block_present(self):
        """@brief Success responses must include _simulation metadata."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers=SEED_HEADERS,
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        sim = r.json()["_simulation"]
        assert sim["simulated"] is True
        assert isinstance(sim["carrier"], str)
        assert isinstance(sim["latencyMs"], (int, float))
