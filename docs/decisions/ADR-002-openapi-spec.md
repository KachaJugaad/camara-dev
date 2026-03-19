# ADR-002: OpenAPI Spec — CAMARA Fall25 Compliance

**Status:** Accepted
**Date:** 2026-03-19
**Author:** Architect Agent

## Context

CAMARA defines OpenAPI 3.0 specs for each API surface. The sandbox must be
spec-compliant so developers can trust that code working against the sandbox
will work against real carrier endpoints.

The CAMARA Fall25 meta-release bumped all surfaces to v1 and introduced
breaking changes from Spring25 (v0):
- SIM Swap: added `/check` endpoint, `maxAge` constraints
- Number Verification: unchanged schema, version bump
- Device Location: renamed to "location-verification", removed UNKNOWN enum value

## Decision

### Implement CAMARA Fall25 v1 endpoints

| Surface | Path | Response Schema |
|---|---|---|
| SIM Swap retrieve-date | `POST /sim-swap/v1/retrieve-date` | `SimSwapInfo` — `latestSimChange` (nullable datetime) |
| SIM Swap check | `POST /sim-swap/v1/check` | `CheckSimSwapInfo` — `swapped` (required boolean) |
| Number Verification | `POST /number-verification/v1/verify` | `NumberVerificationMatchResponse` — `devicePhoneNumberVerified` (bool) |
| Location Verification | `POST /location-verification/v1/verify` | `VerifyLocationResponse` — `verificationResult` (TRUE/FALSE/PARTIAL) |

### Error response schema

All errors follow CAMARA ErrorInfo: `{status: int, code: str, message: str}`.
FastAPI's default `{"detail": ...}` wrapper is overridden via custom exception handler.

### Spec-level decisions

1. **v0 backward compatibility** — Old v0 paths return `301 Moved Permanently`
   with `Deprecation: true` header pointing to the v1 path.

2. **location-verification rename** — `device-location` renamed per CAMARA
   Commonalities Design Guide. Old path `/device-location/v0/verify` redirects
   to `/location-verification/v1/verify`.

3. **x-correlator header** — Echoed on every response per CAMARA Commonalities.
   Auto-generated UUID if not provided by caller.

4. **`_simulation` block** — Sandbox extension (not in CAMARA spec). Appended to
   every success response with: `carrier`, `latencyMs`, `simulated: true`.
   Helps developers see which carrier profile was used and what latency was applied.

5. **SIM Swap maxAge limits** — Spec allows 1-2400 hours. Canadian carriers enforce
   a privacy threshold of 720 hours — requests above that return `OUT_OF_RANGE`.

6. **Location Verification enum** — Fall25 removed `UNKNOWN` from `verificationResult`.
   Only `TRUE`, `FALSE`, `PARTIAL` are valid. `matchRate` (integer 1-99) included
   only for `PARTIAL` results.

## Consequences

- Developers build against real CAMARA contracts — no surprise mismatches
- v0→v1 redirects prevent breaking existing integrations during migration
- `_simulation` block is clearly namespaced and won't conflict with CAMARA fields
- Conformance tests validate spec compliance on every CI run
