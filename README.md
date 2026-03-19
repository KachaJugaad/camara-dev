# camara-dev — Canada's Open CAMARA Telco API Sandbox
# https://kachajugaad.github.io/camara-dev/

[![Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)
[![CAMARA Fall25](https://img.shields.io/badge/CAMARA-Fall25-purple)](https://camaraproject.org)
[![Tests](https://img.shields.io/badge/tests-63_passing-green)](tests/)
[![Substack](https://img.shields.io/badge/Substack-Read_Post-orange)](https://substack.com/home/post/p-191454486)

Test SIM swap detection, number verification, and device location against
realistic Rogers, Bell, and Telus simulation — no carrier agreement needed.

CAMARA Fall25 spec-compliant. All endpoints use v1 paths, CAMARA ErrorInfo
schema, and spec-accurate response fields.

---

## First API call in 90 seconds

```bash
# 1. Clone and start
git clone https://github.com/KachaJugaad/camara-dev
cd camara-dev
docker compose up

# 2. Detect a SIM swap (demo key — no sign-up needed)
curl -X POST http://localhost:8080/sim-swap/v1/retrieve-date \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100"}'

# Response — realistic Rogers behavior with ~120ms latency:
# {
#   "latestSimChange": null,
#   "_simulation": {"carrier": "Rogers", "latencyMs": 143.2, "simulated": true}
# }
```

Open **http://localhost:8080/docs** for interactive Swagger UI, or
**http://localhost:3000** for the developer portal.

---

## What is CAMARA?

[CAMARA](https://camaraproject.org) is a global initiative (GSMA + Linux
Foundation) that standardizes telecom APIs. Instead of proprietary carrier
interfaces, CAMARA defines one universal spec.

**The problem:** Rogers, Bell, and Telus haven't published developer sandboxes.
If you're building fraud detection or identity verification with telco signals,
you have nowhere to test.

**This sandbox fills that gap** with realistic carrier simulation.

---

## API surfaces

### UC1 — SIM Swap Detection

Detect if a SIM card was recently swapped — the #1 signal for account takeover.

```bash
# When was the SIM last swapped?
curl -X POST http://localhost:8080/sim-swap/v1/retrieve-date \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100"}'

# Was it swapped in the last 24 hours? (boolean)
curl -X POST http://localhost:8080/sim-swap/v1/check \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100", "maxAge": 24}'
```

### UC2 — Number Verification

Verify a phone number matches the SIM in a device — no SMS code needed.

```bash
curl -X POST http://localhost:8080/number-verification/v1/verify \
  -H "Authorization: Bearer demo-sandbox-key-bell" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+16135550100"}'
```

### UC3 — Location Verification

Check if a device is within a geographic area using cell tower data.

```bash
curl -X POST http://localhost:8080/location-verification/v1/verify \
  -H "Authorization: Bearer demo-sandbox-key-telus" \
  -H "Content-Type: application/json" \
  -d '{
    "device": {"phoneNumber": "+16045550100"},
    "area": {
      "areaType": "CIRCLE",
      "center": {"latitude": 49.2827, "longitude": -123.1207},
      "radius": 10000
    }
  }'
```

### UC4 — Fraud Score (sandbox-only)

Combine all 3 signals into one risk score (0-100). Not part of CAMARA spec.

```bash
curl -X POST http://localhost:8080/sandbox/fraud-score \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{
    "phoneNumber": "+14165550100",
    "location": {"latitude": 43.6532, "longitude": -79.3832, "radiusMeters": 5000}
  }'
```

### UC5 — Developer Portal

React web UI at **http://localhost:3000** with:
- Instant API key signup (no email verification)
- Live playground — select a surface, fill params, click "Try it"
- Copy-paste SDK snippets for curl, Python, and Node.js

---

## Demo keys

No sign-up required. Use these immediately:

| Key | Carrier | Best for |
|-----|---------|----------|
| `demo-sandbox-key-rogers` | Rogers | Toronto (+1416) |
| `demo-sandbox-key-bell` | Bell | Ottawa/Montreal (+1613) |
| `demo-sandbox-key-telus` | Telus | Vancouver (+1604) |
| `demo-sandbox-key-auto` | Auto-detect | Detects from MSISDN prefix |

Get your own key:
```bash
curl -X POST http://localhost:8080/sandbox/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@yourcompany.ca"}'
```

---

## Carrier simulation profiles

| Carrier | p50 latency | p95 latency | Timeout rate | SIM swap delay |
|---------|------------|------------|-------------|----------------|
| Rogers  | 120ms | 340ms | 4.5% | 2 hours |
| Bell    | 145ms | 410ms | 3.8% | 3 hours |
| Telus   | 105ms | 295ms | 2.8% | 1 hour |

All configurable in `config/carriers/*.toml`. Add a carrier = one TOML file,
zero code changes.

---

## Architecture

```
Client (curl / SDK / Portal)
    |
    v
FastAPI (main.py)
    |-- CAMARA headers middleware (x-correlator, spec version)
    |-- auth.py (validate bearer token)
    |-- carriers/loader.py (resolve carrier from key or MSISDN)
    |-- engine.py (latency injection + error injection via seeded RNG)
    |-- surfaces/*.py (build CAMARA-spec response)
    |
    v
Response + _simulation metadata
```

**Phase 1 (current):** Python/FastAPI simulation MVP.
**Phase 2 (planned):** Rust simulation engine + Go API gateway.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details and
[docs/decisions/](docs/decisions/) for Architecture Decision Records.

---

## Run tests

```bash
# Install dependencies
pip install -r src/simulation/requirements.txt

# All tests (63 total)
pytest tests/ -v

# By category
pytest tests/unit/ -v           # 30 unit tests
pytest tests/integration/ -v    # 21 integration tests
pytest tests/conformance/ -v    # 12 conformance tests
```

---

## Project structure

```
camara-dev/
├── src/simulation/app/     # FastAPI application
│   ├── main.py             # CAMARA surface endpoints
│   ├── sandbox_routes.py   # Sandbox management endpoints
│   ├── fraud_score.py      # Chained fraud scoring
│   ├── engine.py           # Latency + error injection
│   ├── auth.py             # Bearer token validation
│   ├── carriers/           # TOML-driven carrier profiles
│   └── surfaces/           # CAMARA response builders
├── src/portal/dev/         # React developer portal (Vite)
├── config/carriers/        # Rogers, Bell, Telus TOML configs
├── config/openapi/         # CAMARA OpenAPI specs
├── config/mcp/             # MCP tool definitions
├── tests/                  # Unit + integration + conformance
├── docs/                   # Architecture docs + ADRs
├── scripts/                # Demo scripts + orchestration
└── docker-compose.yml      # One command to run everything
```

---

## CAMARA spec compliance

| Surface | Endpoint | Spec | Status |
|---------|----------|------|--------|
| SIM Swap | `/sim-swap/v1/retrieve-date` | Fall25 v1.0 | Compliant |
| SIM Swap | `/sim-swap/v1/check` | Fall25 v1.0 | Compliant |
| Number Verify | `/number-verification/v1/verify` | Fall25 v1.0 | Compliant |
| Location | `/location-verification/v1/verify` | Fall25 v1.0 | Compliant |
| Error Schema | All endpoints | CAMARA ErrorInfo | Compliant |
| Headers | x-correlator, spec version | Commonalities | Compliant |

**Auth note:** This sandbox uses API key bearer tokens for convenience.
Production CAMARA requires CIBA. See `GET /sandbox/auth-migration-guide`.

---

## License

Apache 2.0 — same license as CAMARA upstream.

## Contributing

Issues and PRs welcome at
[github.com/KachaJugaad/camara-dev](https://github.com/KachaJugaad/camara-dev).
