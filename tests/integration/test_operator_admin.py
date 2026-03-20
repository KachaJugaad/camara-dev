"""
tests/integration/test_operator_admin.py — Operator + Admin endpoint tests.

@file   test_operator_admin.py
@brief  UC6: Tests for operator onboarding wizard and admin dashboard APIs.
@usage  pytest tests/integration/test_operator_admin.py -v
"""

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


# ── Operator onboarding ──────────────────────────────────────────────────────


class TestOperatorOnboarding:
    """@brief UC6: Operator self-onboarding wizard tests."""

    def test_register_operator(self):
        """@brief POST /operator/register creates a new operator."""
        r = client.post(
            "/operator/register",
            json={
                "organizationName": "Test Carrier",
                "contactEmail": "test@carrier.ca",
                "carrierName": "testcarrier",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "onboarding_started"
        assert body["currentStep"] == 1
        assert body["totalSteps"] == 8
        assert "operatorId" in body

    def test_register_rejects_missing_fields(self):
        """@brief Registration without required fields returns 400."""
        r = client.post("/operator/register", json={"organizationName": "X"})
        assert r.status_code == 400

    def test_complete_step(self):
        """@brief Completing step 2 advances the wizard."""
        reg = client.post(
            "/operator/register",
            json={
                "organizationName": "Step Test",
                "contactEmail": "step@test.ca",
                "carrierName": "steptest",
            },
        ).json()
        op_id = reg["operatorId"]

        r = client.post(
            f"/operator/step/{op_id}/2",
            json={"msisdnPrefixes": "1416,1647"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["stepCompleted"] == 2
        assert body["currentStep"] == 3

    def test_get_status(self):
        """@brief GET /operator/status returns progress."""
        reg = client.post(
            "/operator/register",
            json={
                "organizationName": "Status Test",
                "contactEmail": "status@test.ca",
                "carrierName": "statustest",
            },
        ).json()
        r = client.get(f"/operator/status/{reg['operatorId']}")
        assert r.status_code == 200
        assert r.json()["totalSteps"] == 8

    def test_list_operators(self):
        """@brief GET /operator/list returns registered operators."""
        r = client.get("/operator/list")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── Admin dashboard ──────────────────────────────────────────────────────────


class TestAdminDashboard:
    """@brief UC6: Admin dashboard API tests."""

    def test_admin_stats(self):
        """@brief GET /admin/stats returns usage statistics."""
        r = client.get("/admin/stats")
        assert r.status_code == 200
        body = r.json()
        assert "totalApiCalls" in body
        assert "errorRate" in body
        assert "developerSignups" in body

    def test_admin_usage(self):
        """@brief GET /admin/usage returns per-endpoint breakdown."""
        r = client.get("/admin/usage")
        assert r.status_code == 200
        assert "endpoints" in r.json()

    def test_admin_recent(self):
        """@brief GET /admin/recent returns recent call log."""
        r = client.get("/admin/recent")
        assert r.status_code == 200
        assert "calls" in r.json()
