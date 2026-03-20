# camara-dev — Canada's Open CAMARA Telco API Sandbox
# https://kachajugaad.github.io/camara-dev/

[![Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)
[![CAMARA Fall25](https://img.shields.io/badge/CAMARA-Fall25-purple)](https://camaraproject.org)
[![Tests](https://img.shields.io/badge/tests-71_passing-green)](tests/)
[![Substack](https://img.shields.io/badge/Substack-Read_Post-orange)](https://substack.com/home/post/p-191454486)

Test SIM swap detection, number verification, and device location against
realistic Rogers, Bell, and Telus simulation — no carrier agreement needed.

CAMARA Fall25 spec-compliant. 25 API endpoints. 3 web portals. 1 CLI.

---

## First API call in 90 seconds

```bash
# 1. Clone and start (starts API + 3 portals)
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

## Three portals, one command

`docker compose up` starts everything:

| Portal | URL | For |
|--------|-----|-----|
| **Developer Portal** | [localhost:3000](http://localhost:3000) | API key signup, live playground, SDK snippets |
| **Operator Wizard** | [localhost:3001](http://localhost:3001) | 8-step carrier onboarding flow |
| **Admin Dashboard** | [localhost:3002](http://localhost:3002) | Usage stats, error rates, operator status |
| **Swagger Docs** | [localhost:8080/docs](http://localhost:8080/docs) | Interactive API documentation |

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

React web UI at **http://localhost:3000** — get an API key, test endpoints
in the live playground, copy SDK snippets for curl/Python/Node.js.

### UC6 — Operator Onboarding + Admin Dashboard

**Operator wizard** at **http://localhost:3001** — 8-step guided flow:
Account → MSISDN ranges → Latency → Error rates → Features → Endpoint → Test → Publish

```bash
# Or use the API directly:
curl -X POST http://localhost:8080/operator/register \
  -H "Content-Type: application/json" \
  -d '{"organizationName":"Rogers","contactEmail":"eng@rogers.com","carrierName":"rogers"}'
```

**Admin dashboard** at **http://localhost:3002** — usage counts, error rates,
developer signups, operator status. Auto-refreshes every 10 seconds.

```bash
curl http://localhost:8080/admin/stats    # Overall stats
curl http://localhost:8080/admin/usage    # Per-endpoint breakdown
curl http://localhost:8080/admin/recent   # Last 50 API calls
```

---

## CLI

```bash
python scripts/camara-cli.py sim-swap  --phone +14165550100
python scripts/camara-cli.py verify    --phone +16135550100
python scripts/camara-cli.py location  --phone +16045550100 --lat 49.28 --lon -123.12
python scripts/camara-cli.py fraud     --phone +14165550100
python scripts/camara-cli.py carriers
```

---

## Demo keys

No sign-up required:

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
Client (curl / SDK / CLI / Portal)
    |
    v
FastAPI (main.py) — :8080
    |-- CAMARA headers middleware (x-correlator, spec version)
    |-- auth.py (bearer token validation)
    |-- sandbox_routes.py (key issuance, carrier listing)
    |-- fraud_score.py (chained 3-signal scoring)
    |-- operator_routes.py (8-step onboarding wizard)
    |-- admin_routes.py (usage stats, error rates)
    |-- carriers/loader.py (TOML-driven carrier profiles)
    |-- engine.py (latency + error injection via seeded RNG)
    |-- surfaces/*.py (CAMARA-spec response builders)
    v
Response + _simulation metadata

Portals: dev (:3000) | operator (:3001) | admin (:3002)
```

**Phase 1 (current):** Python/FastAPI simulation MVP.
**Phase 2 (planned):** Rust simulation engine + Go API gateway.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details and
[docs/decisions/](docs/decisions/) for Architecture Decision Records.

---

## Run tests

```bash
pip install -r src/simulation/requirements.txt

# All tests (71 total)
pytest tests/ -v

# By category
pytest tests/unit/ -v           # 27 unit tests
pytest tests/integration/ -v    # 34 integration tests
pytest tests/conformance/ -v    # 10 conformance tests
```

---

## Project structure

```
camara-dev/
├── src/simulation/app/        # FastAPI application
│   ├── main.py                # CAMARA surface endpoints (v1)
│   ├── sandbox_routes.py      # Key issuance, carrier listing
│   ├── fraud_score.py         # Chained fraud scoring (UC4)
│   ├── operator_routes.py     # 8-step onboarding wizard (UC6)
│   ├── admin_routes.py        # Usage stats dashboard (UC6)
│   ├── engine.py              # Latency + error injection
│   ├── auth.py                # Bearer token validation
│   ├── carriers/              # TOML-driven carrier profiles
│   └── surfaces/              # CAMARA response builders
├── src/portal/
│   ├── dev/                   # Developer portal (:3000)
│   ├── operator/              # Operator wizard (:3001)
│   └── admin/                 # Admin dashboard (:3002)
├── scripts/
│   ├── camara-cli.py          # CLI for all operations
│   └── demo_agent_fraud_check.py
├── config/carriers/           # Rogers, Bell, Telus TOML configs
├── config/openapi/            # CAMARA OpenAPI specs
├── config/mcp/                # MCP tool definitions
├── tests/
│   ├── unit/                  # 27 tests
│   ├── integration/           # 34 tests
│   └── conformance/           # 10 tests
├── docs/
│   ├── ARCHITECTURE.md
│   └── decisions/             # ADR-001, ADR-002
└── docker-compose.yml         # One command to run everything
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
