"""
sandbox_routes.py — Sandbox management endpoints.

@file   sandbox_routes.py
@brief  API key issuance, carrier listing, health check, auth migration guide.
@detail These endpoints are sandbox-specific (not part of CAMARA spec).
        They help developers get started quickly and understand the sandbox.

@usage  Mounted on the main FastAPI app via app.include_router().
"""

from fastapi import APIRouter, HTTPException

from carriers import get_registry
from auth import issue_key


router = APIRouter(tags=["sandbox"])


@router.get("/")
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
            "POST /sandbox/keys with " '{"email": "you@example.ca"} to get a key'
        ),
        "demo_keys": {
            "rogers": "demo-sandbox-key-rogers",
            "bell": "demo-sandbox-key-bell",
            "telus": "demo-sandbox-key-telus",
            "auto": "demo-sandbox-key-auto",
        },
        "github": "https://github.com/KachaJugaad/camara-dev",
    }


@router.get("/health")
async def health():
    """
    @brief  Health check for load balancers and monitoring.
    @return Dict with "ok" status and count of loaded carriers.
    """
    registry = get_registry()
    return {"status": "ok", "carriers_loaded": len(registry.list_names())}


@router.post("/sandbox/keys")
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


@router.get("/sandbox/carriers")
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


@router.get("/sandbox/auth-migration-guide")
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
                "https://github.com/camaraproject/" "IdentityAndConsentManagement"
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
