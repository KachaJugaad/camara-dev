"""
conftest.py — Shared pytest fixtures for CAMARA sandbox test suite.

@file   conftest.py
@brief  Provides common fixtures used across unit, integration, and
        conformance tests. Auto-discovered by pytest — no import needed.
@detail All fixtures are stateless and independent. Session-scoped fixtures
        (carrier_registry) avoid re-reading TOML files for every test.

@note   Fixture order within a test class is not guaranteed — use
        explicit dependencies via fixture parameters.
"""

import os
import sys
import pytest

# Ensure src/simulation/app is on the path for imports
_APP_DIR = os.path.join(
    os.path.dirname(__file__), "..", "src", "simulation", "app"
)
sys.path.insert(0, os.path.abspath(_APP_DIR))

# Set working directory to repo root so config/carriers/ resolves
os.chdir(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def carrier_registry():
    """
    @brief  Session-scoped carrier registry — loaded once for all tests.
    @return CarrierRegistry with all carrier profiles from config/carriers/.
    @note   scope=session avoids re-reading TOML files for every test.
    """
    from carriers import CarrierRegistry

    return CarrierRegistry(config_dir="config/carriers")


@pytest.fixture
def rogers(carrier_registry):
    """
    @brief  Rogers carrier profile fixture.
    @return CarrierProfile for Rogers Communications Canada.
    """
    return carrier_registry.get("rogers")


@pytest.fixture
def bell(carrier_registry):
    """
    @brief  Bell carrier profile fixture.
    @return CarrierProfile for Bell Canada.
    """
    return carrier_registry.get("bell")


@pytest.fixture
def telus(carrier_registry):
    """
    @brief  Telus carrier profile fixture.
    @return CarrierProfile for Telus Communications.
    """
    return carrier_registry.get("telus")


@pytest.fixture
def deterministic_engine(rogers):
    """
    @brief  SimulationEngine with seed=42 — fully deterministic for tests.
    @return SimulationEngine bound to Rogers with reproducible RNG.
    @note   Use this when you need reproducible error injection and latency.
    """
    from engine import SimulationEngine

    return SimulationEngine(profile=rogers, seed=42)


@pytest.fixture
def test_client():
    """
    @brief  FastAPI TestClient for integration tests — no server needed.
    @return TestClient wrapping the full app with real carrier profiles.
    @note   Uses real simulation engine, not mocks.
    """
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def rogers_headers():
    """
    @brief  Auth headers for Rogers demo key.
    @return Dict with Authorization and Content-Type headers.
    """
    return {
        "Authorization": "Bearer demo-sandbox-key-rogers",
        "Content-Type": "application/json",
    }


@pytest.fixture
def bell_headers():
    """
    @brief  Auth headers for Bell demo key.
    @return Dict with Authorization and Content-Type headers.
    """
    return {
        "Authorization": "Bearer demo-sandbox-key-bell",
        "Content-Type": "application/json",
    }


@pytest.fixture
def telus_headers():
    """
    @brief  Auth headers for Telus demo key.
    @return Dict with Authorization and Content-Type headers.
    """
    return {
        "Authorization": "Bearer demo-sandbox-key-telus",
        "Content-Type": "application/json",
    }


@pytest.fixture
def toronto_phone():
    """
    @brief  Toronto MSISDN that resolves to Rogers via auto-detect.
    @return E.164 phone number string.
    """
    return "+14165550100"


@pytest.fixture
def ottawa_phone():
    """
    @brief  Ottawa MSISDN that resolves to Bell via auto-detect.
    @return E.164 phone number string.
    """
    return "+16135550100"


@pytest.fixture
def vancouver_phone():
    """
    @brief  Vancouver MSISDN that resolves to Telus via auto-detect.
    @return E.164 phone number string.
    """
    return "+16045550100"


@pytest.fixture
def valid_sim_swap_body(toronto_phone):
    """
    @brief  Valid SIM swap request body for testing.
    @return Dict with phoneNumber and maxAge fields.
    """
    return {"phoneNumber": toronto_phone, "maxAge": 240}


@pytest.fixture
def valid_location_body(toronto_phone):
    """
    @brief  Valid device location request body — Toronto city center.
    @return Dict with device and area (CIRCLE) fields.
    """
    return {
        "device": {"phoneNumber": toronto_phone},
        "area": {
            "areaType": "CIRCLE",
            "center": {"latitude": 43.6532, "longitude": -79.3832},
            "radius": 10000,
        },
    }
