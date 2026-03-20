# MCP Agent Integration Guide

Use CAMARA sandbox surfaces as MCP tools in your AI agent workflows.

## MCP tool definitions

The sandbox exposes 3 MCP tools defined in `config/mcp/tools.json`:

| Tool | Description |
|------|-------------|
| `camara_verify_number` | Verify a phone number is active on a Canadian carrier |
| `camara_detect_sim_swap` | Detect if a SIM was recently swapped |
| `camara_get_device_location` | Get approximate device location |

## Using with an AI agent

Each MCP tool maps to a CAMARA HTTP endpoint:

```python
# Example: AI agent fraud check using all 3 tools
import httpx

BASE = "http://localhost:8080"
HEADERS = {"Authorization": "Bearer demo-sandbox-key-auto"}

# Tool 1: Check SIM swap
sim = httpx.post(f"{BASE}/sim-swap/v1/retrieve-date",
    headers=HEADERS,
    json={"phoneNumber": "+14165550100"}).json()

# Tool 2: Verify number
num = httpx.post(f"{BASE}/number-verification/v1/verify",
    headers=HEADERS,
    json={"phoneNumber": "+14165550100"}).json()

# Tool 3: Check location
loc = httpx.post(f"{BASE}/location-verification/v1/verify",
    headers=HEADERS,
    json={"device": {"phoneNumber": "+14165550100"},
          "area": {"areaType": "CIRCLE",
                   "center": {"latitude": 43.65, "longitude": -79.38},
                   "radius": 10000}}).json()

# Or use the combined fraud score endpoint
fraud = httpx.post(f"{BASE}/sandbox/fraud-score",
    headers=HEADERS,
    json={"phoneNumber": "+14165550100",
          "location": {"latitude": 43.65, "longitude": -79.38,
                       "radiusMeters": 5000}}).json()

print(f"Risk: {fraud['riskScore']}/100 ({fraud['riskLevel']})")
```

## Demo script

Run the pre-built demo:
```bash
python scripts/demo_agent_fraud_check.py
```

This calls all 3 surfaces and prints a formatted fraud assessment.
