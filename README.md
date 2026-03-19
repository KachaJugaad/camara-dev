# camara-dev — Canada's Open CAMARA Telco API Sandbox

[![Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)
[![CAMARA Fall25](https://img.shields.io/badge/CAMARA-Fall25-purple)](https://camaraproject.org)
[![Simulated](https://img.shields.io/badge/mode-simulation-green)](https://github.com/KachaJugaad/camara-dev)

Canada's first open-source CAMARA API sandbox. Test SIM swap detection, number
verification, and location verification against realistic Rogers, Bell, and Telus
simulation profiles — no carrier agreement, no approval process, no cost.

**CAMARA Fall25 spec-compliant.** All endpoints use v1 paths, CAMARA ErrorInfo schema,
and spec-accurate response fields.

---

## The network already knows. Nobody can ask it.

A woman in Montreal wakes up to a dead phone. She restarts it. Goes about her morning. By the time she calls Rogers three hours later, someone has already used her number to reset her banking passwords, bypass two-factor, and move forty thousand dollars out of her accounts.

The carrier logged the SIM swap at 2am. The timestamp is sitting in a database right now. Her bank had no idea.

Not because the information wasn't there. Because nobody asked.

---

**A developer in Waterloo** spent three weeks trying to understand the carrier authentication flow for SIM swap detection. He gave up and shipped SMS OTP instead. He knew it was less secure. He shipped it anyway because he couldn't figure out how to do better. His users are less safe today because the information that would protect them is locked behind a procurement process.

**A fintech in Toronto** built a loan application system that verifies phone numbers during sign-up. They wanted to confirm the number actually belonged to the device submitting the application. The technical capability exists inside every Canadian carrier's IMS core. The developer portal to access it does not. They shipped without verification. Three months later, a fraud ring used spoofed numbers to submit two hundred applications in a single weekend.

**An e-commerce company in Vancouver** wanted to check whether a buyer's phone was actually in the same city as the shipping address before approving high-value orders. The network knows where the device is. Cell tower triangulation has been accurate to city-level for over a decade. The company couldn't get a test environment from any Canadian carrier. They built nothing. They eat the chargebacks.

---

**The pattern is the same every time.** The network has the answer. The developer can't ask the question. Not because the technology doesn't exist. Because there's no sandbox, no test environment, no documentation written for someone who doesn't already work in telecommunications.

This sandbox exists so that stops being true.

Three API calls. Three questions the network already knows the answer to.

---

## First API call in 90 seconds

```bash
# 1. Clone and start
git clone https://github.com/KachaJugaad/camara-dev
cd camara-dev
docker compose up

# 2. Use a built-in demo key — no sign-up needed
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

Or open **http://localhost:8080/docs** for the interactive Swagger UI.

---

## Demo keys (no sign-up required)

| Key | Carrier | Use for |
|-----|---------|---------|
| `demo-sandbox-key-rogers` | Rogers | Toronto MSISDN testing |
| `demo-sandbox-key-bell` | Bell | Ottawa/Montreal testing |
| `demo-sandbox-key-telus` | Telus | Vancouver/Calgary testing |
| `demo-sandbox-key-auto` | Auto-detect | Detects carrier from MSISDN prefix |

Get your own key (also instant):
```bash
curl -X POST http://localhost:8080/sandbox/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@yourcompany.ca"}'
```

---

## Use cases

### UC1 — SIM swap fraud detection

*The bank's fraud system runs forty machine learning models on every wire transfer. None of them ask the one question that would actually matter: did someone steal this customer's phone number twenty minutes ago? One API call. The carrier already has the answer.*

**Retrieve date** (was there a swap?):
```bash
curl -X POST http://localhost:8080/sim-swap/v1/retrieve-date \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100"}'
```

**Check** (boolean — did a swap occur within N hours?):
```bash
curl -X POST http://localhost:8080/sim-swap/v1/check \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100", "maxAge": 24}'
```

---

### UC2 — Phone number verification

*A user types their phone number into your app. You send them an SMS code. They type the code back. You call this "verification." Meanwhile, the network knows — without sending anything, without asking the user to do anything — whether that number belongs to the SIM in that device. You just can't ask.*

```bash
curl -X POST http://localhost:8080/number-verification/v1/verify \
  -H "Authorization: Bearer demo-sandbox-key-bell" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+16135550100"}'
```

---

### UC3 — Location verification

*A customer claims they're in Toronto. Their GPS says Toronto. A ten-dollar app from the Play Store can make any GPS say Toronto. But the cell tower the phone is actually connected to? That's in Bucharest. The network knows. Your fraud system doesn't.*

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

---

### UC4 — Chained fraud score (all 3 signals)

*SIM swapped two hours ago. Phone number doesn't match the device. GPS says Toronto, cell tower says overseas. Any one of those signals is a red flag. All three together? That's not a customer. That's someone emptying an account. Three API calls. One score. The network had the answer the whole time.*

```bash
curl -X POST http://localhost:8080/sandbox/fraud-score \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{
    "phoneNumber": "+14165550100",
    "location": {"latitude": 43.6532, "longitude": -79.3832, "radiusMeters": 5000}
  }'
```

---

## CAMARA spec compliance

This sandbox implements CAMARA Fall25 meta-release specifications:
- SIM Swap v1.0 (two operations: /retrieve-date and /check)
- Number Verification v1.0
- Location Verification v1.0 (renamed from device-location per CAMARA Design Guide)

Spec source: github.com/camaraproject

| Surface | Endpoint | Spec version | Compliant | Notes |
|---------|----------|-------------|-----------|-------|
| SIM Swap | POST /sim-swap/v1/retrieve-date | Fall25 v1.0 | Yes | |
| SIM Swap | POST /sim-swap/v1/check | Fall25 v1.0 | Yes | Added |
| Number Verify | POST /number-verification/v1/verify | Fall25 v1.0 | Yes | |
| Location | POST /location-verification/v1/verify | Fall25 v1.0 | Yes | Renamed |
| Auth | Bearer token | Sandbox simplified | Documented | CIBA guide added |

### Sandbox auth vs production auth
This sandbox uses API key bearer tokens for developer convenience.
Production CAMARA uses CIBA (Client-Initiated Backchannel Authentication).
See `GET /sandbox/auth-migration-guide` for the exact flow your code needs
when moving to a real carrier endpoint.

---

## Carrier simulation profiles

| Carrier | p50 latency | p95 latency | Timeout rate | SIM swap delay |
|---------|------------|------------|-------------|----------------|
| Rogers  | 120ms | 340ms | 4.5% | 2 hours |
| Bell    | 145ms | 410ms | 3.8% | 3 hours |
| Telus   | 105ms | 295ms | 2.8% | 1 hour |

All values configurable in `config/carriers/*.toml`.

---

## Run tests

```bash
pip install -r src/simulation/requirements.txt

# Unit tests (27 tests)
pytest tests/unit/ -v

# Integration tests (26 tests)
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

---

## Architecture

```
Request -> FastAPI (main.py)
        -> CAMARA headers middleware (spec version, x-correlator)
        -> auth.py (validate bearer token)
        -> carriers/ (resolve carrier profile from key or MSISDN)
        -> engine.py (apply latency + error injection)
        -> surfaces/*.py (build CAMARA-spec response)
        -> Response
```

Stack: Python/FastAPI (simulation MVP). Rust planned for production engine (Phase 2).
All carrier behavior is config-driven (TOML) — zero code changes to add a carrier.

---

## License

Apache 2.0 — same license as CAMARA upstream.

## Contributing

Issues and PRs welcome at [github.com/KachaJugaad/camara-dev](https://github.com/KachaJugaad/camara-dev).
