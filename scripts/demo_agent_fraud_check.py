#!/usr/bin/env python3
"""
scripts/demo_agent_fraud_check.py — Day 4: Agent fraud check demo.

@file   demo_agent_fraud_check.py
@brief  Calls all 3 CAMARA surfaces and the chained fraud-score endpoint.
@detail Demonstrates how an AI agent or developer would use the sandbox
        to assess fraud risk using SIM swap, number verification, and
        device location signals.

@usage  python scripts/demo_agent_fraud_check.py
@note   Requires the sandbox to be running on localhost:8080.
        Start with: docker compose up
"""

import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8080"
API_KEY = "demo-sandbox-key-rogers"
PHONE = "+14165550100"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def call_api(path: str, body: dict) -> dict:
    """
    @brief   Make a POST request to the sandbox API.
    @param   path  API path (e.g. "/sim-swap/v1/retrieve-date").
    @param   body  Request body dict.
    @return  Parsed JSON response dict.
    @raises  SystemExit  If the server is unreachable.
    """
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        if "Connection refused" in str(e):
            print("ERROR: Sandbox not running. Start with: docker compose up")
            sys.exit(1)
        raise


def print_signal(name: str, result: dict) -> None:
    """
    @brief   Print a single CAMARA signal result.
    @param   name    Signal name for display.
    @param   result  API response dict.
    """
    print(f"\n--- {name} ---")
    print(json.dumps(result, indent=2))


def main() -> None:
    """
    @brief   Run all 3 CAMARA signals and the chained fraud score.
    @detail  Calls each surface individually, then the combined endpoint.
             Prints formatted output for each step.
    """
    print(f"CAMARA Fraud Check Demo — Phone: {PHONE}")
    print(f"Carrier: Rogers (auto-detected from +1416 prefix)")
    print("=" * 50)

    # Signal 1: SIM Swap
    sim_swap = call_api(
        "/sim-swap/v1/retrieve-date",
        {"phoneNumber": PHONE},
    )
    print_signal("SIM Swap Detection", sim_swap)

    # Signal 2: Number Verification
    num_verify = call_api(
        "/number-verification/v1/verify",
        {"phoneNumber": PHONE},
    )
    print_signal("Number Verification", num_verify)

    # Signal 3: Location Verification
    location = call_api(
        "/location-verification/v1/verify",
        {
            "device": {"phoneNumber": PHONE},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": 43.6532, "longitude": -79.3832},
                "radius": 10000,
            },
        },
    )
    print_signal("Location Verification", location)

    # Combined: Fraud Score
    fraud = call_api(
        "/sandbox/fraud-score",
        {
            "phoneNumber": PHONE,
            "location": {
                "latitude": 43.6532,
                "longitude": -79.3832,
                "radiusMeters": 10000,
            },
        },
    )

    print("\n" + "=" * 50)
    print("FRAUD RISK ASSESSMENT")
    print("=" * 50)
    print(f"  Risk Score:  {fraud['riskScore']}/100")
    print(f"  Risk Level:  {fraud['riskLevel']}")
    if fraud["riskFactors"]:
        print(f"  Factors:     {', '.join(fraud['riskFactors'])}")
    else:
        print("  Factors:     None detected")
    print(f"  Carrier:     {fraud['carrier']}")
    print()


if __name__ == "__main__":
    main()
