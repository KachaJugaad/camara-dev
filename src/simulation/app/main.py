"""
main.py — CAMARA Canada Sandbox simulation server (Fall25 spec-compliant).

@file   main.py
@brief  FastAPI app exposing CAMARA Fall25 endpoints with carrier simulation.
@detail SIM Swap v1, Number Verification v1, Location Verification v1.
        Sandbox management and fraud-score in separate router modules.

@usage  uvicorn main:app --reload --port 8080
"""

import sys
import os
import uuid
import random as _rng_mod
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from engine import SimulationEngine
from carriers import get_registry, CarrierProfile
from auth import get_claims, TokenClaims
from surfaces import sim_swap, number_verify, location_verification
from sandbox_routes import router as sandbox_router
from fraud_score import router as fraud_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """@brief Load carrier profiles once at startup."""
    registry = get_registry()
    print(f"CAMARA sandbox ready. Carriers: {', '.join(registry.list_names())}")
    yield


app = FastAPI(
    title="CAMARA Canada Sandbox",
    description="Canada's first open-source CAMARA telco API sandbox.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sandbox_router)
app.include_router(fraud_router)


@app.exception_handler(HTTPException)
async def camara_error_handler(request: Request, exc: HTTPException):
    """
    @brief   Return CAMARA ErrorInfo instead of FastAPI default.
    @spec    CAMARA_common.yaml: {status: int, code: str, message: str}.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "code": "INTERNAL",
            "message": str(exc.detail),
        },
    )


@app.middleware("http")
async def add_camara_headers(request: Request, call_next):
    """@brief Add CAMARA spec headers + x-correlator to every response."""
    response = await call_next(request)
    response.headers["X-CAMARA-Spec-Version"] = "Fall25"
    response.headers["X-CAMARA-API-Version"] = "1.0.0"
    response.headers["X-CAMARA-Simulated"] = "true"
    response.headers["X-CAMARA-Auth-Mode"] = "sandbox-simplified"
    correlator = request.headers.get("x-correlator")
    response.headers["x-correlator"] = correlator or str(uuid.uuid4())
    return response


# ── Shared helpers ────────────────────────────────────────────────────────────


def _resolve(claims: TokenClaims, phone: str) -> CarrierProfile:
    """@brief Resolve carrier from token override or MSISDN auto-detect."""
    reg = get_registry()
    return (
        reg.get(claims.carrier_override)
        if claims.carrier_override
        else reg.auto_detect(phone)
    )


def _seed(request: Request) -> int | None:
    """@brief Extract optional X-Seed header for deterministic tests."""
    raw = request.headers.get("X-Seed")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _err(status: int, code: str, message: str) -> JSONResponse:
    """@brief CAMARA ErrorInfo response helper."""
    return JSONResponse(
        status_code=status,
        content={
            "status": status,
            "code": code,
            "message": message,
        },
    )


def _sim_block(carrier, result) -> dict:
    """@brief Build _simulation metadata to append to responses."""
    return {
        "carrier": carrier.display_name,
        "latencyMs": round(result.latency_ms, 1),
        "simulated": True,
    }


async def _run_surface(
    request, claims, phone, surface_name, body, feature_flag, feature_label
):
    """
    @brief   Shared flow: resolve carrier → check feature → run engine.
    @return  Tuple of (carrier, SimResult) on success, or JSONResponse on error.
    """
    carrier = _resolve(claims, phone)
    if not getattr(carrier, feature_flag):
        return _err(
            422,
            "SERVICE_NOT_APPLICABLE",
            f"{carrier.display_name} does not support {feature_label}",
        )
    engine = SimulationEngine(profile=carrier, seed=_seed(request))
    result = await engine.run(surface_name, body)
    if not result.success:
        return _err(
            504 if result.error_code == "TIMEOUT" else 503,
            result.error_code,
            result.error_message,
        )
    return {**result.data, "_simulation": _sim_block(carrier, result)}


# ── UC1: SIM Swap Detection (v1) ─────────────────────────────────────────────


@app.post(
    "/sim-swap/v1/retrieve-date",
    tags=["UC1 — SIM swap"],
    summary="Retrieve date of most recent SIM swap",
)
async def retrieve_sim_swap_date(
    request: Request, body: dict, claims: TokenClaims = Depends(get_claims)
):
    """@brief UC1: Return latestSimChange for a phone number."""
    errs = sim_swap.validate_request(body)
    if errs:
        return _err(400, "INVALID_ARGUMENT", "; ".join(errs))
    return await _run_surface(
        request,
        claims,
        body["phoneNumber"],
        "sim_swap",
        body,
        "sim_swap_supported",
        "SIM swap detection",
    )


@app.post(
    "/sim-swap/v1/check",
    tags=["UC1 — SIM swap"],
    summary="Check if SIM swap occurred within a period",
)
async def check_sim_swap(
    request: Request, body: dict, claims: TokenClaims = Depends(get_claims)
):
    """@brief UC1: Return swapped boolean for maxAge window."""
    errs = sim_swap.validate_check_request(body)
    if errs:
        return _err(400, "INVALID_ARGUMENT", "; ".join(errs))
    phone = body.get("phoneNumber", "")
    if not phone:
        return _err(422, "MISSING_IDENTIFIER", "phoneNumber required")
    max_age = body.get("maxAge", 240)
    if max_age > sim_swap.CARRIER_PRIVACY_THRESHOLD_HOURS:
        return _err(400, "OUT_OF_RANGE", f"maxAge {max_age}h exceeds privacy threshold")
    return await _run_surface(
        request,
        claims,
        phone,
        "sim_swap_check",
        body,
        "sim_swap_supported",
        "SIM swap detection",
    )


# ── UC2: Number Verification (v1) ────────────────────────────────────────────


@app.post(
    "/number-verification/v1/verify",
    tags=["UC2 — Number verification"],
    summary="Verify a phone number matches the device SIM",
)
async def verify_number(
    request: Request, body: dict, claims: TokenClaims = Depends(get_claims)
):
    """@brief UC2: Return devicePhoneNumberVerified boolean."""
    errs = number_verify.validate_request(body)
    if errs:
        return _err(400, "INVALID_ARGUMENT", "; ".join(errs))
    return await _run_surface(
        request,
        claims,
        body["phoneNumber"],
        "number_verify",
        body,
        "number_verification_supported",
        "number verification",
    )


# ── UC3: Location Verification (v1) ──────────────────────────────────────────


@app.post(
    "/location-verification/v1/verify",
    tags=["UC3 — Location"],
    summary="Verify whether a device is within a geographic area",
)
async def verify_location(
    request: Request, body: dict, claims: TokenClaims = Depends(get_claims)
):
    """@brief UC3: Return verificationResult enum (TRUE/FALSE/PARTIAL)."""
    errs = location_verification.validate_request(body)
    if errs:
        return _err(400, "INVALID_ARGUMENT", "; ".join(errs))
    phone = body.get("device", {}).get("phoneNumber", "")
    if not phone:
        return _err(
            422, "MISSING_IDENTIFIER", "device.phoneNumber required in 2-legged flow"
        )
    rng = _rng_mod.Random()
    if not location_verification.check_max_age_fulfillable(body, rng):
        return _err(
            422,
            "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE",
            "Fresh location cannot be provided at this time",
        )
    return await _run_surface(
        request,
        claims,
        phone,
        "location_verification",
        body,
        "device_location_supported",
        "location verification",
    )


# ── v0 deprecated redirects → v1 ─────────────────────────────────────────────


def _v0_redirect(url: str) -> RedirectResponse:
    """@brief Create a 301 redirect with Deprecation header."""
    r = RedirectResponse(url=url, status_code=301)
    r.headers["Deprecation"] = "true"
    return r


@app.post("/sim-swap/v0/retrieve-date", include_in_schema=False)
async def redir_sim_swap_date():
    """@brief v0 → v1 redirect."""
    return _v0_redirect("/sim-swap/v1/retrieve-date")


@app.post("/sim-swap/v0/check", include_in_schema=False)
async def redir_sim_swap_check():
    """@brief v0 → v1 redirect."""
    return _v0_redirect("/sim-swap/v1/check")


@app.post("/number-verification/v0/verify", include_in_schema=False)
async def redir_number_verify():
    """@brief v0 → v1 redirect."""
    return _v0_redirect("/number-verification/v1/verify")


@app.post("/device-location/v0/verify", include_in_schema=False)
async def redir_device_location():
    """@brief v0 → v1 redirect (renamed to location-verification)."""
    return _v0_redirect("/location-verification/v1/verify")
