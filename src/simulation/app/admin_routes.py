"""
admin_routes.py — Admin dashboard endpoints.

@file   admin_routes.py
@brief  UC6: Usage stats, error rates, developer pipeline for admin dashboard.
@detail Tracks API call counts, error rates, and developer signups in-memory.
        Provides aggregate stats for the admin dashboard UI.

@usage  GET /admin/stats — overall sandbox statistics
        GET /admin/usage — per-endpoint usage breakdown
"""

import time
from collections import defaultdict

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["UC6 — Admin dashboard"])

# In-memory counters — reset on server restart
_CALL_LOG: list[dict] = []
_SIGNUP_COUNT: int = 0


def record_call(endpoint: str, carrier: str, status: int, latency_ms: float):
    """
    @brief   Record an API call for admin stats.
    @param   endpoint    The API path called.
    @param   carrier     Carrier name used.
    @param   status      HTTP status code returned.
    @param   latency_ms  Response latency in milliseconds.
    """
    _CALL_LOG.append(
        {
            "endpoint": endpoint,
            "carrier": carrier,
            "status": status,
            "latency_ms": latency_ms,
            "timestamp": time.time(),
        }
    )


def record_signup():
    """@brief Increment developer signup counter."""
    global _SIGNUP_COUNT
    _SIGNUP_COUNT += 1


@router.get("/stats")
async def get_stats():
    """
    @brief   Overall sandbox statistics for the admin dashboard.
    @return  Dict with total calls, error rate, developer count, uptime.
    """
    total = len(_CALL_LOG)
    errors = sum(1 for c in _CALL_LOG if c["status"] >= 400)
    error_rate = (errors / total * 100) if total > 0 else 0.0

    carriers = defaultdict(int)
    for c in _CALL_LOG:
        carriers[c["carrier"]] += 1

    return {
        "totalApiCalls": total,
        "errorRate": round(error_rate, 1),
        "developerSignups": _SIGNUP_COUNT,
        "carriersActive": dict(carriers),
        "endpointsAvailable": 5,
        "surfaces": {
            "simSwap": {"retrieveDate": True, "check": True},
            "numberVerification": {"verify": True},
            "locationVerification": {"verify": True},
            "fraudScore": True,
        },
    }


@router.get("/usage")
async def get_usage():
    """
    @brief   Per-endpoint usage breakdown for the admin dashboard.
    @return  Dict with per-endpoint call counts and avg latency.
    """
    by_endpoint: dict[str, list] = defaultdict(list)
    for c in _CALL_LOG:
        by_endpoint[c["endpoint"]].append(c)

    result = {}
    for endpoint, calls in by_endpoint.items():
        latencies = [c["latency_ms"] for c in calls]
        errors = sum(1 for c in calls if c["status"] >= 400)
        result[endpoint] = {
            "totalCalls": len(calls),
            "errors": errors,
            "avgLatencyMs": round(sum(latencies) / len(latencies), 1),
            "p95LatencyMs": round(
                sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 1
            ),
        }

    return {"endpoints": result, "totalCalls": len(_CALL_LOG)}


@router.get("/recent")
async def get_recent():
    """
    @brief   Last 50 API calls for the admin live feed.
    @return  List of recent call records.
    """
    return {"calls": _CALL_LOG[-50:][::-1]}
