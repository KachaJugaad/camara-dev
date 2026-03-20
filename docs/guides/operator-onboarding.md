# Operator Onboarding Guide

Register your carrier's CAMARA endpoint through the 8-step wizard.

## Option A: Web wizard

1. Start the sandbox: `docker compose up`
2. Open `http://localhost:3001`
3. Follow the 8 steps:

| Step | What | What you need |
|------|------|---------------|
| 1 | Account Registration | Organization name, email, carrier name |
| 2 | MSISDN Ranges | Your phone number prefixes (e.g. 1416, 1647) |
| 3 | Latency Profile | p50/p95/p99 latency targets in ms |
| 4 | Error Profile | Timeout and unavailable error rates (0-1) |
| 5 | Feature Flags | Which CAMARA surfaces you support |
| 6 | Endpoint Registration | Your real CAMARA API URL (optional) |
| 7 | Test Verification | Run conformance tests against your config |
| 8 | Publish | Make your profile available to developers |

## Option B: API

```bash
# Register
curl -X POST http://localhost:8080/operator/register \
  -H "Content-Type: application/json" \
  -d '{
    "organizationName": "Rogers Communications",
    "contactEmail": "engineer@rogers.com",
    "carrierName": "rogers"
  }'
# Returns: {"operatorId": "op-abc123...", ...}

# Complete step 2 (MSISDN ranges)
curl -X POST http://localhost:8080/operator/step/op-abc123/2 \
  -H "Content-Type: application/json" \
  -d '{"msisdnPrefixes": "1416,1647,1437"}'

# Check progress
curl http://localhost:8080/operator/status/op-abc123

# List all operators
curl http://localhost:8080/operator/list
```

## After onboarding

Once all 8 steps are complete:
- Your carrier profile is stored in the sandbox
- Developers can test against your simulated latency/error profile
- If you registered a real endpoint (step 6), the sandbox can passthrough
  requests to your actual CAMARA API instead of simulating
