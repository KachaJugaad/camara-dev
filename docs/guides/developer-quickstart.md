# Developer Quickstart

Get from zero to your first CAMARA API call in under 2 minutes.

## Prerequisites

- Docker installed ([get Docker](https://docs.docker.com/get-docker/))
- curl or any HTTP client

## Step 1: Start the sandbox

```bash
git clone https://github.com/KachaJugaad/camara-dev
cd camara-dev
docker compose up
```

This starts:
- API server on `localhost:8080`
- Developer portal on `localhost:3000`
- Operator wizard on `localhost:3001`
- Admin dashboard on `localhost:3002`

## Step 2: Make your first call

Use a demo key (no signup needed):

```bash
curl -X POST http://localhost:8080/sim-swap/v1/retrieve-date \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+14165550100"}'
```

## Step 3: Try all three surfaces

```bash
# Number verification
curl -X POST http://localhost:8080/number-verification/v1/verify \
  -H "Authorization: Bearer demo-sandbox-key-bell" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+16135550100"}'

# Location verification
curl -X POST http://localhost:8080/location-verification/v1/verify \
  -H "Authorization: Bearer demo-sandbox-key-telus" \
  -H "Content-Type: application/json" \
  -d '{"device":{"phoneNumber":"+16045550100"},"area":{"areaType":"CIRCLE","center":{"latitude":49.28,"longitude":-123.12},"radius":10000}}'

# Combined fraud score
curl -X POST http://localhost:8080/sandbox/fraud-score \
  -H "Authorization: Bearer demo-sandbox-key-rogers" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber":"+14165550100","location":{"latitude":43.65,"longitude":-79.38,"radiusMeters":5000}}'
```

## Step 4: Get your own API key

```bash
curl -X POST http://localhost:8080/sandbox/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.ca"}'
```

## Step 5: Use the web playground

Open `http://localhost:3000` — select a surface, fill in parameters,
click "Try it", and copy the SDK snippet for your language.

## Demo keys

| Key | Carrier |
|-----|---------|
| `demo-sandbox-key-rogers` | Rogers |
| `demo-sandbox-key-bell` | Bell |
| `demo-sandbox-key-telus` | Telus |
| `demo-sandbox-key-auto` | Auto-detect from phone number |

## CLI alternative

```bash
python scripts/camara-cli.py sim-swap --phone +14165550100
python scripts/camara-cli.py verify --phone +16135550100
python scripts/camara-cli.py fraud --phone +14165550100
```

## Next steps

- Read the [Architecture](../ARCHITECTURE.md) for system design
- See [ADR-001](../decisions/ADR-001-system-design.md) for design decisions
- Check [Plain English guide](../PLAIN_ENGLISH.md) for non-technical overview
