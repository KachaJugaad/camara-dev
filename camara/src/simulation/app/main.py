"""
main.py — CAMARA Canada Sandbox simulation server (Fall25 spec-compliant).

@file   main.py
@brief  FastAPI application exposing CAMARA Fall25 spec-compliant API endpoints
        backed by configurable Canadian carrier simulation.
@detail Implements CAMARA Fall25 meta-release:
        - SIM Swap v1 (retrieve-date + check)
        - Number Verification v1
        - Location Verification v1 (renamed from device-location per spec)
        All error responses use CAMARA ErrorInfo schema (status=int, code=str).

@usage  uvicorn main:app --reload --port 8080
@try    curl -X POST http://localhost:8080/sim-swap/v1/retrieve-date
          -H "Authorization: Bearer demo-sandbox-key-rogers"
          -H "Content-Type: application/json"
          -d '{"phoneNumber": "+14165550100"}'
"""

import sys
import os
import uuid
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from engine import SimulationEngine
from carriers import get_registry, CarrierProfile
from auth import get_claims, issue_key, TokenClaims
from surfaces import sim_swap, number_verify, location_verification


# ── App lifecycle ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    @brief  Load carrier profiles once at startup.
    @detail Prints loaded carrier names to stdout for operator confirmation.
    """
    registry = get_registry()
    print(
        f"CAMARA sandbox ready (Fall25 spec). "
        f"Carriers: {', '.join(registry.list_names())}"
    )
    yield


app = FastAPI(
    title="CAMARA Canada Sandbox",
    description=(
        "Canada's first open-source CAMARA telco API sandbox. "
        "CAMARA Fall25 spec-compliant. "
        "Realistic Rogers, Bell, and Telus simulation — "
        "no carrier agreement needed. Apache 2.0 — "
        "github.com/KachaJugaad/camara-dev"
    ),
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


# ── Fix 1: Override HTTPException handler for CAMARA ErrorInfo schema ─────────
# FastAPI wraps HTTPException.detail in {"detail": ...}. CAMARA requires
# ErrorInfo at the top level: {"status": int, "code": str, "message": str}.


@app.exception_handler(HTTPException)
async def camara_http_exception_handler(request: Request, exc: HTTPException):
    """
    @brief   Override default HTTPException to return CAMARA ErrorInfo.
    @spec    CAMARA_common.yaml: ErrorInfo — status=int, code=str, message=str.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "code": "INTERNAL",
            "message": str(exc.detail),
        },
    )


# ── Fix 7: CAMARA spec version headers on every response ─────────────────────
# CAMARA Commonalities Design Guide: x-correlator header for E2E observability


@app.middleware("http")
async def add_camara_headers(request: Request, call_next):
    """
    @brief   Add CAMARA spec version headers to every response.
    @detail  Adds X-CAMARA-Spec-Version, X-CAMARA-API-Version,
             X-CAMARA-Simulated, X-CAMARA-Auth-Mode, and x-correlator.
    @spec    CAMARA Commonalities Design Guide — x-correlator header.
             Fix 7: spec version headers on every response.
             Fix 5: X-CAMARA-Auth-Mode for sandbox auth transparency.
    """
    response = await call_next(request)
    response.headers["X-CAMARA-Spec-Version"] = "Fall25"
    response.headers["X-CAMARA-API-Version"] = "1.0.0"
    response.headers["X-CAMARA-Simulated"] = "true"
    # Fix 5: CIBA auth transparency
    response.headers["X-CAMARA-Auth-Mode"] = "sandbox-simplified"
    # CAMARA Commonalities: echo x-correlator if provided, else generate
    correlator = request.headers.get("x-correlator")
    if correlator:
        response.headers["x-correlator"] = correlator
    else:
        response.headers["x-correlator"] = str(uuid.uuid4())
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────


def resolve_carrier(claims: TokenClaims, phone_number: str) -> CarrierProfile:
    """
    @brief   Resolve which carrier profile to use for a request.
    @param   claims        Validated token claims (may contain carrier_override).
    @param   phone_number  E.164 phone number for auto-detection fallback.
    @return  CarrierProfile to use for simulation.
    @detail  Priority: 1. Key's carrier_override, 2. Auto-detect from MSISDN.
    """
    registry = get_registry()
    if claims.carrier_override:
        return registry.get(claims.carrier_override)
    return registry.auto_detect(phone_number)


def camara_error(status: int, code: str, message: str) -> JSONResponse:
    """
    @brief   Format an error response per CAMARA ErrorInfo schema.
    @param   status   HTTP status code (integer).
    @param   code     CAMARA error code string (SCREAMING_SNAKE_CASE).
    @param   message  Human-readable error description.
    @return  JSONResponse with status (int), code (str), message (str).
    @spec    CAMARA Commonalities CAMARA_common.yaml — ErrorInfo schema:
             status=integer, code=string, message=string. All required.
    """
    return JSONResponse(
        status_code=status,
        content={"status": status, "code": code, "message": message},
    )


# ── Sandbox management endpoints ──────────────────────────────────────────────


@app.get("/", tags=["sandbox"])
async def root():
    """
    @brief  Sandbox info — carrier list, surfaces, documentation links.
    @return Dict with sandbox metadata and available demo keys.
    """
    registry = get_registry()
    return {
        "name": "CAMARA Canada Sandbox",
        "version": "1.0.0",
        "specVersion": "Fall25",
        "simulated": True,
        "carriers": registry.list_names(),
        "surfaces": [
            "sim-swap",
            "number-verification",
            "location-verification",
        ],
        "docs": "/docs",
        "quickstart": (
            "POST /sandbox/keys with "
            '{"email": "you@example.ca"} to get a key'
        ),
        "demo_keys": {
            "rogers": "demo-sandbox-key-rogers",
            "bell": "demo-sandbox-key-bell",
            "telus": "demo-sandbox-key-telus",
            "auto": "demo-sandbox-key-auto",
        },
        "github": "https://github.com/KachaJugaad/camara-dev",
    }


@app.get("/health", tags=["sandbox"])
async def health():
    """
    @brief  Health check for load balancers and monitoring.
    @return Dict with "ok" status and count of loaded carriers.
    """
    registry = get_registry()
    return {"status": "ok", "carriers_loaded": len(registry.list_names())}


@app.post("/sandbox/keys", tags=["sandbox"])
async def create_key(body: dict):
    """
    @brief   Issue a sandbox API key instantly — no approval needed.
    @param   body  Dict with "email" (required) and "carrier" (optional).
    @return  Dict with apiKey, email, carrier, and usage note.
    @raises  HTTPException(400)  If email is missing or carrier is unknown.
    """
    email = body.get("email", "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")

    carrier = body.get("carrier", None)
    if carrier:
        try:
            get_registry().get(carrier)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown carrier: {carrier}. "
                    f"Available: {get_registry().list_names()}"
                ),
            )

    api_key = issue_key(email, carrier)
    return {
        "apiKey": api_key,
        "email": email,
        "carrier": carrier or "auto (detected from MSISDN prefix)",
        "simulated": True,
        "note": "This is a sandbox key. No real carrier data is accessed.",
        "docs": "/docs",
    }


@app.get("/sandbox/carriers", tags=["sandbox"])
async def list_carriers():
    """
    @brief  List all available carrier profiles with simulation parameters.
    @return Dict mapping carrier name to profile summary.
    """
    registry = get_registry()
    result = {}
    for name in registry.list_names():
        p = registry.get(name)
        result[name] = {
            "displayName": p.display_name,
            "msisdnPrefixes": p.msisdn_prefixes[:5],
            "latency": {
                "p50ms": p.latency_ms.p50,
                "p95ms": p.latency_ms.p95,
                "p99ms": p.latency_ms.p99,
            },
            "errorRates": {
                "timeout": f"{p.error_profiles.timeout_probability:.1%}",
                "serviceUnavailable": (
                    f"{p.error_profiles.service_unavailable_probability:.1%}"
                ),
            },
            "surfaces": {
                "simSwap": p.sim_swap_supported,
                "numberVerification": p.number_verification_supported,
                "locationVerification": p.device_location_supported,
            },
        }
    return result


# ── Fix 5: CIBA auth migration guide ─────────────────────────────────────────


@app.get("/sandbox/auth-migration-guide", tags=["sandbox"])
async def auth_migration_guide():
    """
    @brief   Explain CIBA auth flow for production migration.
    @return  JSON document describing the CIBA flow developers need.
    @spec    CAMARA Security and Interoperability Profile — CIBA required
             for production. Sandbox uses simplified API key bearer tokens.
    """
    return {
        "title": "Migrating from Sandbox Auth to Production CIBA",
        "sandbox_auth": {
            "method": "API key bearer token",
            "header": "Authorization: Bearer <sandbox-key>",
            "note": "Simplified for developer convenience. NOT production-safe.",
        },
        "production_auth": {
            "method": "CIBA (Client-Initiated Backchannel Authentication)",
            "spec": "RFC 7662 + CAMARA Security Profile",
            "flow": [
                "1. POST /bc-authorize with login_hint (phone number)",
                "2. Poll POST /token until auth_req_id resolves",
                "3. Use access_token as Bearer in CAMARA API calls",
                "4. access_token has scope: sim-swap:check, etc.",
            ],
            "reference": (
                "https://github.com/camaraproject/"
                "IdentityAndConsentManagement"
            ),
        },
        "scopes": {
            "sim-swap": [
                "sim-swap:retrieve-date",
                "sim-swap:check",
            ],
            "number-verification": [
                "number-verification:verify",
                "number-verification:device-phone-number:read",
            ],
            "location-verification": [
                "location-verification:verify",
            ],
        },
    }


# ── UC1: SIM Swap Detection (v1) ─────────────────────────────────────────────


@app.post(
    "/sim-swap/v1/retrieve-date",
    tags=["UC1 — SIM swap fraud detection"],
    summary="Retrieve the date of the most recent SIM swap",
)
async def retrieve_sim_swap_date(
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC1: Retrieve date of most recent SIM swap for a phone number.
    @param   body    Request body with phoneNumber (E.164).
    @param   claims  Validated bearer token claims (injected by FastAPI).
    @return  CAMARA SimSwapInfo response with latestSimChange.
    @spec    sim-swap.yaml: POST /retrieve-date — SimSwapInfo response.
    """
    errors = sim_swap.validate_request(body)
    if errors:
        return camara_error(400, "INVALID_ARGUMENT", "; ".join(errors))

    carrier = resolve_carrier(claims, body["phoneNumber"])

    if not carrier.sim_swap_supported:
        return camara_error(
            422,
            "SERVICE_NOT_APPLICABLE",
            f"{carrier.display_name} does not support SIM swap detection",
        )

    engine = SimulationEngine(profile=carrier)
    result = await engine.run("sim_swap", body)

    if not result.success:
        return camara_error(
            504 if result.error_code == "TIMEOUT" else 503,
            result.error_code,
            result.error_message,
        )

    return {
        **result.data,
        "_simulation": {
            "carrier": carrier.display_name,
            "latencyMs": round(result.latency_ms, 1),
            "simulated": True,
        },
    }


@app.post(
    "/sim-swap/v1/check",
    tags=["UC1 — SIM swap fraud detection"],
    summary="Check if SIM swap occurred within a period",
)
async def check_sim_swap(
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC1: Check if SIM swap occurred within maxAge hours.
    @param   body    Request body with phoneNumber and optional maxAge (1-2400).
    @param   claims  Validated bearer token claims.
    @return  CAMARA CheckSimSwapInfo response with swapped (boolean).
    @spec    sim-swap.yaml: POST /check — CheckSimSwapInfo response.
             CreateCheckSimSwap: maxAge integer, min=1, max=2400, default=240.
    """
    errors = sim_swap.validate_check_request(body)
    if errors:
        return camara_error(400, "INVALID_ARGUMENT", "; ".join(errors))

    phone = body.get("phoneNumber", "")
    if not phone:
        return camara_error(
            422,
            "MISSING_IDENTIFIER",
            "phoneNumber required in 2-legged flow",
        )

    # sim-swap.yaml: OUT_OF_RANGE when maxAge exceeds operator privacy threshold
    max_age = body.get("maxAge", 240)
    if max_age > sim_swap.CARRIER_PRIVACY_THRESHOLD_HOURS:
        return camara_error(
            400,
            "OUT_OF_RANGE",
            f"maxAge {max_age}h exceeds carrier privacy threshold "
            f"({sim_swap.CARRIER_PRIVACY_THRESHOLD_HOURS}h for Canadian carriers)",
        )

    carrier = resolve_carrier(claims, phone)

    if not carrier.sim_swap_supported:
        return camara_error(
            422,
            "SERVICE_NOT_APPLICABLE",
            f"{carrier.display_name} does not support SIM swap detection",
        )

    engine = SimulationEngine(profile=carrier)
    result = await engine.run("sim_swap_check", body)

    if not result.success:
        return camara_error(
            504 if result.error_code == "TIMEOUT" else 503,
            result.error_code,
            result.error_message,
        )

    return {
        **result.data,
        "_simulation": {
            "carrier": carrier.display_name,
            "latencyMs": round(result.latency_ms, 1),
            "simulated": True,
        },
    }


# ── UC2: Number Verification (v1) ────────────────────────────────────────────


@app.post(
    "/number-verification/v1/verify",
    tags=["UC2 — Number verification"],
    summary="Verify a phone number matches the device SIM",
)
async def verify_number(
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC2: Verify a phone number matches the SIM in the user's device.
    @param   body    Request body with phoneNumber (E.164).
    @param   claims  Validated bearer token claims.
    @return  CAMARA NumberVerificationMatchResponse with
             devicePhoneNumberVerified (bool).
    @spec    number-verification.yaml: POST /verify —
             NumberVerificationMatchResponse.
    """
    errors = number_verify.validate_request(body)
    if errors:
        return camara_error(400, "INVALID_ARGUMENT", "; ".join(errors))

    carrier = resolve_carrier(claims, body["phoneNumber"])

    if not carrier.number_verification_supported:
        return camara_error(
            422,
            "SERVICE_NOT_APPLICABLE",
            f"{carrier.display_name} does not support number verification",
        )

    engine = SimulationEngine(profile=carrier)
    result = await engine.run("number_verify", body)

    if not result.success:
        return camara_error(
            504 if result.error_code == "TIMEOUT" else 503,
            result.error_code,
            result.error_message,
        )

    return {
        **result.data,
        "_simulation": {
            "carrier": carrier.display_name,
            "latencyMs": round(result.latency_ms, 1),
            "simulated": True,
        },
    }


# ── UC3: Location Verification (v1) ──────────────────────────────────────────
# CAMARA Commonalities Design Guide: api-name is "location-verification"


@app.post(
    "/location-verification/v1/verify",
    tags=["UC3 — Location verification"],
    summary="Verify whether a device is within a geographic area",
)
async def verify_location(
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC3: Verify if a device is within a specified geographic area.
    @param   body    Request body with device.phoneNumber, area, optional maxAge.
    @param   claims  Validated bearer token claims.
    @return  CAMARA VerifyLocationResponse with verificationResult (enum).
    @spec    location-verification.yaml: POST /verify —
             VerifyLocationResponse. verificationResult enum: TRUE/FALSE/PARTIAL.
             matchRate integer 1-99, only for PARTIAL.
    """
    errors = location_verification.validate_request(body)
    if errors:
        return camara_error(400, "INVALID_ARGUMENT", "; ".join(errors))

    phone = body.get("device", {}).get("phoneNumber", "")
    if not phone:
        return camara_error(
            422,
            "MISSING_IDENTIFIER",
            "device.phoneNumber required in 2-legged flow",
        )

    carrier = resolve_carrier(claims, phone)

    if not carrier.device_location_supported:
        return camara_error(
            422,
            "SERVICE_NOT_APPLICABLE",
            f"{carrier.display_name} does not support location verification",
        )

    # location-verification.yaml: 422 UNABLE_TO_FULFILL_MAX_AGE
    import random as _rng_mod

    rng = _rng_mod.Random()
    if not location_verification.check_max_age_fulfillable(body, rng):
        return camara_error(
            422,
            "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE",
            "Fresh location (maxAge=0) cannot be provided at this time",
        )

    engine = SimulationEngine(profile=carrier)
    result = await engine.run("location_verification", body)

    if not result.success:
        return camara_error(
            504 if result.error_code == "TIMEOUT" else 503,
            result.error_code,
            result.error_message,
        )

    return {
        **result.data,
        "_simulation": {
            "carrier": carrier.display_name,
            "latencyMs": round(result.latency_ms, 1),
            "simulated": True,
        },
    }


# ── UC4: Chained fraud scoring (sandbox-only, not CAMARA spec) ───────────────


@app.post(
    "/sandbox/fraud-score",
    tags=["UC4 — Chained fraud signals"],
    summary="Run all 3 CAMARA signals — fraud scoring demo",
)
async def fraud_score(
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC4: Chain all 3 CAMARA signals into a single fraud score.
    @param   body    Request body with phoneNumber and optional location.
    @param   claims  Validated bearer token claims.
    @return  Dict with riskScore (0-100), riskLevel, riskFactors, signals.
    @note    NOT part of CAMARA spec. Sandbox-only convenience endpoint.
    """
    phone = body.get("phoneNumber", "")
    if not phone:
        raise HTTPException(status_code=400, detail="phoneNumber required")

    carrier = resolve_carrier(claims, phone)
    engine = SimulationEngine(profile=carrier)

    sim_result = await engine.run(
        "sim_swap", {"phoneNumber": phone, "maxAge": 24}
    )
    num_result = await engine.run("number_verify", {"phoneNumber": phone})

    loc_body: dict = {
        "device": {"phoneNumber": phone},
        "area": {"areaType": "CIRCLE"},
    }
    loc = body.get("location", {})
    if loc:
        loc_body["area"]["center"] = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
        }
        loc_body["area"]["radius"] = loc.get("radiusMeters", 10000)
    loc_result = await engine.run("location_verification", loc_body)

    risk_score = 0
    risk_factors: list[str] = []

    sim_swap_date = (
        sim_result.data.get("latestSimChange") if sim_result.success else None
    )
    if sim_swap_date:
        risk_score += 40
        risk_factors.append("SIM swapped within 24 hours")

    if num_result.success and not num_result.data.get(
        "devicePhoneNumberVerified", True
    ):
        risk_score += 30
        risk_factors.append("Phone number does not match device SIM")

    if (
        loc_result.success
        and loc_result.data.get("verificationResult") == "FALSE"
    ):
        risk_score += 30
        risk_factors.append("Device not in expected location")

    return {
        "phoneNumber": phone,
        "carrier": carrier.display_name,
        "riskScore": min(risk_score, 100),
        "riskLevel": (
            "HIGH"
            if risk_score >= 60
            else "MEDIUM" if risk_score >= 30 else "LOW"
        ),
        "riskFactors": risk_factors,
        "signals": {
            "simSwap": (
                sim_result.data
                if sim_result.success
                else {"error": sim_result.error_code}
            ),
            "numberVerification": (
                num_result.data
                if num_result.success
                else {"error": num_result.error_code}
            ),
            "locationVerification": (
                loc_result.data
                if loc_result.success
                else {"error": loc_result.error_code}
            ),
        },
        "_simulation": {
            "carrier": carrier.display_name,
            "simulated": True,
        },
    }


# ── Fix 4: v0 deprecated redirects → v1 ──────────────────────────────────────
# Old v0 paths return 301 with Deprecation header for backward compat


@app.post("/sim-swap/v0/retrieve-date", include_in_schema=False)
async def redirect_sim_swap_retrieve_date():
    """@brief Deprecated v0 → v1 redirect for SIM swap retrieve-date."""
    resp = RedirectResponse(
        url="/sim-swap/v1/retrieve-date", status_code=301
    )
    resp.headers["Deprecation"] = "true"
    return resp


@app.post("/sim-swap/v0/check", include_in_schema=False)
async def redirect_sim_swap_check():
    """@brief Deprecated v0 → v1 redirect for SIM swap check."""
    resp = RedirectResponse(url="/sim-swap/v1/check", status_code=301)
    resp.headers["Deprecation"] = "true"
    return resp


@app.post("/number-verification/v0/verify", include_in_schema=False)
async def redirect_number_verify():
    """@brief Deprecated v0 → v1 redirect for number verification."""
    resp = RedirectResponse(
        url="/number-verification/v1/verify", status_code=301
    )
    resp.headers["Deprecation"] = "true"
    return resp


@app.post("/device-location/v0/verify", include_in_schema=False)
async def redirect_device_location():
    """@brief Deprecated v0 → v1 redirect (renamed to location-verification)."""
    resp = RedirectResponse(
        url="/location-verification/v1/verify", status_code=301
    )
    resp.headers["Deprecation"] = "true"
    return resp
