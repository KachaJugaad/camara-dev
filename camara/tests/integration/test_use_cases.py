"""
tests/integration/test_use_cases.py — End-to-end use case integration tests.

@file   test_use_cases.py
@brief  Tests each use case through the full HTTP stack using FastAPI TestClient.
        Updated for CAMARA Fall25 spec: v1 paths, ErrorInfo schema,
        location-verification rename, SIM swap /check endpoint.

@usage  pytest tests/integration/ -v
"""

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)

ROGERS_KEY = "demo-sandbox-key-rogers"
BELL_KEY = "demo-sandbox-key-bell"
TELUS_KEY = "demo-sandbox-key-telus"
AUTO_KEY = "demo-sandbox-key-auto"


# ── Sandbox management ────────────────────────────────────────────────────────


def test_root_returns_carrier_list():
    """@brief GET / must list all three Canadian carriers."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "rogers" in body["carriers"]
    assert "bell" in body["carriers"]
    assert "telus" in body["carriers"]
    assert "location-verification" in body["surfaces"]


def test_health_check_passes():
    """@brief GET /health must return ok status."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_sandbox_key():
    """@brief POST /sandbox/keys must return a new API key instantly."""
    r = client.post("/sandbox/keys", json={"email": "test@startup.ca"})
    assert r.status_code == 200
    body = r.json()
    assert "apiKey" in body
    assert body["apiKey"].startswith("sk-sandbox-")


def test_carrier_list_endpoint():
    """@brief GET /sandbox/carriers must return profiles for all 3 carriers."""
    r = client.get("/sandbox/carriers")
    assert r.status_code == 200
    body = r.json()
    for carrier in ("rogers", "bell", "telus"):
        assert carrier in body
        assert "latency" in body[carrier]


def test_auth_migration_guide():
    """
    @brief  GET /sandbox/auth-migration-guide must return CIBA flow info.
    @spec   Fix 5: CIBA auth documentation.
    """
    r = client.get("/sandbox/auth-migration-guide")
    assert r.status_code == 200
    body = r.json()
    assert "production_auth" in body
    assert body["production_auth"]["method"] == (
        "CIBA (Client-Initiated Backchannel Authentication)"
    )


# ── Fix 7: CAMARA spec version headers ───────────────────────────────────────


def test_response_has_camara_spec_headers():
    """
    @brief  Every response must include X-CAMARA-Spec-Version headers.
    @spec   Fix 7: spec version headers on every response.
    """
    r = client.get("/health")
    assert r.headers["X-CAMARA-Spec-Version"] == "Fall25"
    assert r.headers["X-CAMARA-API-Version"] == "1.0.0"
    assert r.headers["X-CAMARA-Simulated"] == "true"
    assert r.headers["X-CAMARA-Auth-Mode"] == "sandbox-simplified"
    assert "x-correlator" in r.headers


# ── Fix 1: Error response schema ─────────────────────────────────────────────


def test_error_response_uses_camara_error_info():
    """
    @brief  Error responses must have status (int), code (str), message (str).
    @spec   CAMARA_common.yaml: ErrorInfo schema.
    """
    r = client.post(
        "/sim-swap/v1/retrieve-date",
        json={"phoneNumber": "+14165550100"},
    )
    assert r.status_code == 401
    body = r.json()
    assert isinstance(body["status"], int)
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)
    assert body["status"] == 401
    assert body["code"] == "UNAUTHENTICATED"


# ── UC1: SIM Swap Detection (v1) ─────────────────────────────────────────────


class TestUC1SIMSwapFraudDetection:
    """@brief UC1: SIM swap fraud detection via v1 endpoints."""

    def test_sim_swap_happy_path_rogers(self):
        """@brief Rogers SIM swap call must return latestSimChange field."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "latestSimChange" in body
        assert body["latestSimChange"] is None or isinstance(
            body["latestSimChange"], str
        )

    def test_sim_swap_includes_simulation_metadata(self):
        """@brief Response must include _simulation block."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["_simulation"]["carrier"] == "Rogers"
        assert body["_simulation"]["simulated"] is True
        assert body["_simulation"]["latencyMs"] > 0

    def test_sim_swap_rejects_missing_phone(self):
        """@brief SIM swap without phoneNumber must return 400."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={},
        )
        assert r.status_code == 400

    def test_sim_swap_rejects_missing_auth(self):
        """@brief SIM swap without Authorization must return 401."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 401

    def test_sim_swap_bell_uses_bell_profile(self):
        """@brief Bell key must use Bell carrier profile."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers={"Authorization": f"Bearer {BELL_KEY}"},
            json={"phoneNumber": "+16135550100"},
        )
        assert r.status_code == 200
        assert r.json()["_simulation"]["carrier"] == "Bell"

    def test_sim_swap_telus_uses_telus_profile(self):
        """@brief Telus key must use Telus carrier profile."""
        r = client.post(
            "/sim-swap/v1/retrieve-date",
            headers={"Authorization": f"Bearer {TELUS_KEY}"},
            json={"phoneNumber": "+16045550100"},
        )
        assert r.status_code == 200
        assert r.json()["_simulation"]["carrier"] == "Telus"

    def test_sim_swap_check_returns_swapped_boolean(self):
        """
        @brief  POST /sim-swap/v1/check must return swapped (boolean).
        @spec   sim-swap.yaml: CheckSimSwapInfo — swapped required boolean.
        """
        r = client.post(
            "/sim-swap/v1/check",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"phoneNumber": "+14165550100", "maxAge": 24},
        )
        assert r.status_code == 200
        body = r.json()
        assert "swapped" in body
        assert isinstance(body["swapped"], bool)

    def test_sim_swap_check_out_of_range(self):
        """
        @brief  maxAge > 720 (carrier privacy threshold) returns OUT_OF_RANGE.
        @spec   sim-swap.yaml: OUT_OF_RANGE error for privacy limits.
        """
        r = client.post(
            "/sim-swap/v1/check",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"phoneNumber": "+14165550100", "maxAge": 1000},
        )
        assert r.status_code == 400
        assert r.json()["code"] == "OUT_OF_RANGE"


# ── UC2: Number Verification (v1) ────────────────────────────────────────────


class TestUC2NumberVerification:
    """@brief UC2: Phone number verification via v1 endpoint."""

    def test_number_verify_happy_path(self):
        """@brief Number verification must return devicePhoneNumberVerified."""
        r = client.post(
            "/number-verification/v1/verify",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "devicePhoneNumberVerified" in body
        assert isinstance(body["devicePhoneNumberVerified"], bool)

    def test_number_verify_all_carriers(self):
        """@brief Number verify must work with all carrier keys."""
        for key, carrier_name in [
            (ROGERS_KEY, "Rogers"),
            (BELL_KEY, "Bell"),
            (TELUS_KEY, "Telus"),
        ]:
            r = client.post(
                "/number-verification/v1/verify",
                headers={"Authorization": f"Bearer {key}"},
                json={"phoneNumber": "+14165550100"},
            )
            assert r.status_code == 200, f"Failed for {carrier_name}"
            assert r.json()["_simulation"]["carrier"] == carrier_name

    def test_number_verify_auto_detect_by_msisdn(self):
        """@brief Auto key must detect Rogers from +1416 MSISDN prefix."""
        r = client.post(
            "/number-verification/v1/verify",
            headers={"Authorization": f"Bearer {AUTO_KEY}"},
            json={"phoneNumber": "+14165550100"},
        )
        assert r.status_code == 200
        assert r.json()["_simulation"]["carrier"] == "Rogers"


# ── UC3: Location Verification (v1) ──────────────────────────────────────────


class TestUC3LocationVerification:
    """
    @brief  UC3: Device location verification via v1 endpoint.
    @spec   CAMARA Commonalities: api-name is "location-verification".
    """

    TORONTO_PAYLOAD = {
        "device": {"phoneNumber": "+14165550100"},
        "area": {
            "areaType": "CIRCLE",
            "center": {"latitude": 43.6532, "longitude": -79.3832},
            "radius": 10000,
        },
    }

    def test_location_verification_happy_path(self):
        """
        @brief  Location verification must return verificationResult enum.
        @spec   location-verification.yaml: TRUE/FALSE/PARTIAL (no UNKNOWN).
        """
        r = client.post(
            "/location-verification/v1/verify",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json=self.TORONTO_PAYLOAD,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verificationResult"] in ("TRUE", "FALSE", "PARTIAL")

    def test_location_verification_has_last_location_time(self):
        """
        @brief  Response must include lastLocationTime (required per spec).
        @spec   location-verification.yaml: lastLocationTime is required.
        """
        r = client.post(
            "/location-verification/v1/verify",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json=self.TORONTO_PAYLOAD,
        )
        assert r.status_code == 200
        assert "lastLocationTime" in r.json()

    def test_location_verification_rejects_invalid_latitude(self):
        """@brief Latitude > 90 must be rejected with 400."""
        bad_payload = {
            "device": {"phoneNumber": "+14165550100"},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": 200, "longitude": -79.38},
                "radius": 5000,
            },
        }
        r = client.post(
            "/location-verification/v1/verify",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json=bad_payload,
        )
        assert r.status_code == 400

    def test_location_verification_rejects_missing_area(self):
        """@brief Request without area must be rejected with 400."""
        r = client.post(
            "/location-verification/v1/verify",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={"device": {"phoneNumber": "+14165550100"}},
        )
        assert r.status_code == 400


# ── Fix 4: v0 deprecated redirects ───────────────────────────────────────────


def test_v0_sim_swap_redirects_to_v1():
    """
    @brief  Old /sim-swap/v0/ path must redirect to v1 with 301.
    @spec   Fix 4: v0→v1 migration with Deprecation header.
    """
    r = client.post(
        "/sim-swap/v0/retrieve-date",
        headers={"Authorization": f"Bearer {ROGERS_KEY}"},
        json={"phoneNumber": "+14165550100"},
        follow_redirects=False,
    )
    assert r.status_code == 301
    assert "/sim-swap/v1/retrieve-date" in r.headers.get("location", "")
    assert r.headers.get("Deprecation") == "true"


def test_v0_device_location_redirects_to_location_verification():
    """
    @brief  Old /device-location/v0/ redirects to /location-verification/v1/.
    @spec   Fix 3 + Fix 4: rename + version bump.
    """
    r = client.post(
        "/device-location/v0/verify",
        headers={"Authorization": f"Bearer {ROGERS_KEY}"},
        json={
            "device": {"phoneNumber": "+14165550100"},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": 43.65, "longitude": -79.38},
                "radius": 5000,
            },
        },
        follow_redirects=False,
    )
    assert r.status_code == 301
    assert "/location-verification/v1/verify" in r.headers.get(
        "location", ""
    )


# ── UC4: Chained fraud score ─────────────────────────────────────────────────


class TestUC4ChainedFraudScore:
    """@brief UC4: All 3 CAMARA signals chained into a fraud score."""

    def test_fraud_score_returns_risk_level(self):
        """@brief Fraud score must return riskScore and riskLevel."""
        r = client.post(
            "/sandbox/fraud-score",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={
                "phoneNumber": "+14165550100",
                "location": {
                    "latitude": 43.6532,
                    "longitude": -79.3832,
                    "radiusMeters": 5000,
                },
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "riskScore" in body
        assert body["riskLevel"] in ("LOW", "MEDIUM", "HIGH")
        assert 0 <= body["riskScore"] <= 100
        assert "signals" in body
        assert "simSwap" in body["signals"]
        assert "numberVerification" in body["signals"]
        assert "locationVerification" in body["signals"]

    def test_fraud_score_rejects_missing_phone(self):
        """@brief Fraud score without phoneNumber must return 400."""
        r = client.post(
            "/sandbox/fraud-score",
            headers={"Authorization": f"Bearer {ROGERS_KEY}"},
            json={},
        )
        assert r.status_code == 400
