#!/usr/bin/env python3
"""
camara-cli.py — Command-line interface for the CAMARA sandbox.

@file   camara-cli.py
@brief  UC6: Single-binary CLI for all CAMARA sandbox operations.
@detail Wraps the sandbox HTTP API so operators and developers can
        interact from the terminal without curl.

@usage  python scripts/camara-cli.py sim-swap --phone +14165550100
        python scripts/camara-cli.py verify --phone +16135550100
        python scripts/camara-cli.py location --phone +16045550100 --lat 49.28 --lon -123.12
        python scripts/camara-cli.py fraud --phone +14165550100
        python scripts/camara-cli.py carriers
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8080"
DEFAULT_KEY = "demo-sandbox-key-auto"


def _post(path: str, body: dict, key: str) -> dict:
    """
    @brief   POST to the sandbox API and return parsed JSON.
    @param   path  API path.
    @param   body  Request body.
    @param   key   API key for Authorization header.
    @return  Parsed response dict.
    """
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except urllib.error.URLError:
        print("Error: Cannot reach sandbox. Start with: docker compose up")
        sys.exit(1)


def _get(path: str) -> dict:
    """
    @brief   GET from the sandbox API.
    @param   path  API path.
    @return  Parsed response dict.
    """
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
            return json.loads(resp.read())
    except urllib.error.URLError:
        print("Error: Cannot reach sandbox. Start with: docker compose up")
        sys.exit(1)


def _print(data: dict):
    """@brief Pretty-print a JSON response."""
    print(json.dumps(data, indent=2))


def cmd_sim_swap(args):
    """@brief Run SIM swap detection."""
    result = _post(
        "/sim-swap/v1/retrieve-date",
        {"phoneNumber": args.phone},
        args.key,
    )
    _print(result)


def cmd_verify(args):
    """@brief Run number verification."""
    result = _post(
        "/number-verification/v1/verify",
        {"phoneNumber": args.phone},
        args.key,
    )
    _print(result)


def cmd_location(args):
    """@brief Run location verification."""
    result = _post(
        "/location-verification/v1/verify",
        {
            "device": {"phoneNumber": args.phone},
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": args.lat, "longitude": args.lon},
                "radius": args.radius,
            },
        },
        args.key,
    )
    _print(result)


def cmd_fraud(args):
    """@brief Run chained fraud score."""
    body = {"phoneNumber": args.phone}
    if args.lat and args.lon:
        body["location"] = {
            "latitude": args.lat,
            "longitude": args.lon,
            "radiusMeters": args.radius,
        }
    result = _post("/sandbox/fraud-score", body, args.key)
    _print(result)


def cmd_carriers(args):
    """@brief List available carrier profiles."""
    _print(_get("/sandbox/carriers"))


def main():
    """@brief Parse CLI args and dispatch to the right command."""
    p = argparse.ArgumentParser(
        prog="camara-cli",
        description="CAMARA Canada Sandbox CLI",
    )
    p.add_argument(
        "--key", default=DEFAULT_KEY,
        help="API key (default: demo-sandbox-key-auto)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # sim-swap
    s = sub.add_parser("sim-swap", help="Detect SIM swap")
    s.add_argument("--phone", required=True, help="E.164 phone number")
    s.set_defaults(func=cmd_sim_swap)

    # verify
    s = sub.add_parser("verify", help="Verify phone number")
    s.add_argument("--phone", required=True, help="E.164 phone number")
    s.set_defaults(func=cmd_verify)

    # location
    s = sub.add_parser("location", help="Verify device location")
    s.add_argument("--phone", required=True, help="E.164 phone number")
    s.add_argument("--lat", type=float, required=True, help="Latitude")
    s.add_argument("--lon", type=float, required=True, help="Longitude")
    s.add_argument("--radius", type=int, default=10000, help="Radius in meters")
    s.set_defaults(func=cmd_location)

    # fraud
    s = sub.add_parser("fraud", help="Chained fraud score")
    s.add_argument("--phone", required=True, help="E.164 phone number")
    s.add_argument("--lat", type=float, help="Latitude")
    s.add_argument("--lon", type=float, help="Longitude")
    s.add_argument("--radius", type=int, default=5000, help="Radius in meters")
    s.set_defaults(func=cmd_fraud)

    # carriers
    s = sub.add_parser("carriers", help="List carrier profiles")
    s.set_defaults(func=cmd_carriers)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
