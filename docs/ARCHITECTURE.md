# CAMARA Canada Sandbox — Architecture

> Single source of truth for system design.
> Maintained by the Architect agent. Last updated: 2026-03-19.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client (curl / SDK / Portal)          │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│              FastAPI Application (main.py)               │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │  Auth    │ │ CAMARA   │ │  Sandbox   │ │ Fraud    │ │
│  │ (auth.py)│ │ Headers  │ │ Management │ │ Score    │ │
│  └────┬─────┘ └──────────┘ └────────────┘ └──────────┘ │
│       │                                                  │
│  ┌────▼─────────────────────────────────────────────┐   │
│  │           Simulation Engine (engine.py)            │   │
│  │  • Latency injection (seeded RNG, percentile lerp)│   │
│  │  • Error injection (probabilistic per carrier)    │   │
│  └────┬──────────────┬──────────────┬───────────────┘   │
│       │              │              │                    │
│  ┌────▼────┐   ┌─────▼────┐  ┌─────▼──────────┐        │
│  │SIM Swap │   │Number    │  │Location        │        │
│  │Surface  │   │Verify    │  │Verification    │        │
│  │         │   │Surface   │  │Surface         │        │
│  └─────────┘   └──────────┘  └────────────────┘        │
└─────────────────────────┬───────────────────────────────┘
                          │ reads at startup
┌─────────────────────────▼───────────────────────────────┐
│          Carrier Profiles (config/carriers/*.toml)       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ Rogers  │  │  Bell   │  │  Telus  │                 │
│  │ .toml   │  │  .toml  │  │  .toml  │                 │
│  └─────────┘  └─────────┘  └─────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## Request Flow

1. Client sends `POST /sim-swap/v1/retrieve-date` with `Authorization: Bearer <key>`
2. **Auth layer** validates bearer token, extracts `TokenClaims` (email, carrier override)
3. **Carrier resolution** picks profile: explicit override > MSISDN prefix auto-detect
4. **Simulation engine** applies carrier profile:
   - Samples latency from percentile distribution (p50→p95→p99→p999)
   - Sleeps for sampled latency (realistic network delay)
   - Probabilistically injects errors (timeout, unavailable, auth, roaming)
5. **Surface builder** constructs CAMARA-spec response body
6. **Response** includes `_simulation` metadata block + CAMARA headers

## Layers

### Auth (`src/simulation/app/auth.py`)
- Validates `Bearer` tokens against in-memory key store
- Demo keys pre-loaded for all 3 carriers + auto-detect
- `POST /sandbox/keys` issues keys instantly (no email verification)
- Returns CAMARA ErrorInfo on all failure paths

### Simulation Engine (`src/simulation/app/engine.py`)
- Takes a `CarrierProfile` and optional RNG `seed`
- Latency: linear interpolation between percentile anchors
- Errors: checked in priority order (timeout > unavailable > auth > roaming)
- Returns `SimResult` dataclass with success/error state + response data

### Surfaces (`src/simulation/app/surfaces/`)
- `sim_swap.py` — SIM Swap v1: retrieve-date + check
- `number_verify.py` — Number Verification v1: verify
- `location_verification.py` — Location Verification v1: verify
- Each surface has: `build_response()`, `validate_request()`, constants

### Carrier Profiles (`config/carriers/*.toml`)
- TOML-driven configuration — no code changes to add carriers
- Fields: MSISDN prefixes, latency percentiles, error probabilities, feature flags
- Loaded once at startup by `CarrierRegistry` singleton

## Testing Strategy

| Layer | Location | What it tests |
|---|---|---|
| Unit | `tests/unit/` | Carrier loading, latency sampling, error injection, validation |
| Integration | `tests/integration/` | Full HTTP stack via FastAPI TestClient |
| Conformance | `tests/conformance/` | CAMARA spec schema compliance |

All tests use `X-Seed` header for deterministic behavior (no flaky tests).

## Phase 2 Migration Plan

| Component | Phase 1 (MVP) | Phase 2 |
|---|---|---|
| Simulation engine | Python | Rust |
| API gateway | FastAPI | Go |
| Auth | Python (in-process) | Go (separate service) |
| Carrier profiles | TOML (unchanged) | TOML (unchanged) |
| OpenAPI contracts | Same | Same |
| Conformance tests | Same | Same |

Phase 2 starts only after MVP is validated. The OpenAPI specs and conformance
tests are the bridge — Phase 2 code must pass identical tests.
