"""
auth.py — Bearer token validation and sandbox API key management.

@file   auth.py
@brief  Validates bearer tokens on every CAMARA API request. Issues sandbox
        keys instantly so developers can make their first API call in <4 min.
@detail In production: tokens validated against a real OAuth2 server.
        In sandbox: deterministic tokens tied to an email address.

SANDBOX AUTH NOTE: This sandbox uses simple API key bearer tokens for developer
convenience. Production CAMARA requires CIBA (RFC 7662 + CAMARA Security Profile).
When migrating to a real carrier endpoint, replace this auth with the CIBA flow:
POST /bc-authorize → poll POST /token → use access_token as Bearer.
See: https://github.com/camaraproject/IdentityAndConsentManagement

@usage  # As FastAPI dependency:
        claims: TokenClaims = Depends(get_claims)
        # Direct validation:
        claims = validate_bearer("Bearer sk-sandbox-...")

@note   Sandbox tokens are NOT secure for production use.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request


@dataclass
class TokenClaims:
    """
    @brief  Claims extracted from a validated bearer token.
    @field  api_key           The raw API key string.
    @field  email             Email address the key was issued to.
    @field  carrier_override  If set, forces a specific carrier for this key.
                              None means auto-detect from MSISDN prefix.
    @field  issued_at         Unix timestamp when the key was created.
    @field  is_sandbox        Always True in sandbox mode.
    """

    api_key: str
    email: str
    carrier_override: Optional[str]
    issued_at: float
    is_sandbox: bool = True


# In-memory key store — replace with database in production
_KEY_STORE: dict[str, dict] = {
    "demo-sandbox-key-rogers": {
        "email": "demo@camara.dev",
        "carrier_override": "rogers",
        "issued_at": time.time(),
    },
    "demo-sandbox-key-bell": {
        "email": "demo@camara.dev",
        "carrier_override": "bell",
        "issued_at": time.time(),
    },
    "demo-sandbox-key-telus": {
        "email": "demo@camara.dev",
        "carrier_override": "telus",
        "issued_at": time.time(),
    },
    "demo-sandbox-key-auto": {
        "email": "demo@camara.dev",
        "carrier_override": None,
        "issued_at": time.time(),
    },
}


def issue_key(email: str, carrier_override: Optional[str] = None) -> str:
    """
    @brief   Issue a new sandbox API key for the given email address.
    @param   email             Developer's email address.
    @param   carrier_override  Optional carrier name to lock this key to.
    @return  API key string prefixed with "sk-sandbox-".
    @detail  Key is deterministic: same email always produces the same key.
             This makes re-registration idempotent — developers can call
             this endpoint multiple times safely.
    @note    Keys are stored in-memory only. Server restart clears issued keys
             (demo keys persist because they are hard-coded).
    """
    raw = f"camara-sandbox:{email}:{carrier_override or 'auto'}"
    api_key = "sk-sandbox-" + hashlib.sha256(raw.encode()).hexdigest()[:32]

    _KEY_STORE[api_key] = {
        "email": email,
        "carrier_override": carrier_override,
        "issued_at": time.time(),
    }

    return api_key


def validate_bearer(authorization: Optional[str]) -> TokenClaims:
    """
    @brief   Validate a bearer token from the Authorization header.
    @param   authorization  Full header value, e.g. "Bearer sk-sandbox-...".
    @return  TokenClaims on success.
    @raises  HTTPException(401)  If token is missing, malformed, or unknown.
    @detail  Accepts "Bearer sk-sandbox-..." or "Bearer demo-sandbox-key-...".
             Returns CAMARA Problem Details on all failure paths.
    """
    # CAMARA Commonalities CAMARA_common.yaml: ErrorInfo schema
    # status=integer, code=string, message=string — all required
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "status": 401,
                "code": "UNAUTHENTICATED",
                "message": (
                    "Authorization header required. "
                    "Format: Bearer <api-key>. "
                    "Get a free sandbox key at POST /sandbox/keys "
                    "or use demo-sandbox-key-auto"
                ),
            },
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "status": 401,
                "code": "UNAUTHENTICATED",
                "message": "Malformed Authorization header",
            },
        )

    api_key = parts[1].strip()
    record = _KEY_STORE.get(api_key)

    if not record:
        raise HTTPException(
            status_code=401,
            detail={
                "status": 401,
                "code": "UNAUTHENTICATED",
                "message": (
                    f"API key not recognized: {api_key[:16]}... "
                    "Get a free key at POST /sandbox/keys"
                ),
            },
        )

    return TokenClaims(
        api_key=api_key,
        email=record["email"],
        carrier_override=record.get("carrier_override"),
        issued_at=record["issued_at"],
    )


def get_claims(request: Request) -> TokenClaims:
    """
    @brief   FastAPI dependency: extract and validate bearer token from Request.
    @param   request  FastAPI Request object.
    @return  TokenClaims with validated token data.
    @raises  HTTPException(401)  If Authorization header is invalid.
    @usage   In route: claims: TokenClaims = Depends(get_claims)
    """
    auth_header = request.headers.get("Authorization")
    return validate_bearer(auth_header)
