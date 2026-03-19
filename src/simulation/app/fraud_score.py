"""
fraud_score.py — Chained fraud scoring endpoint (sandbox-only).

@file   fraud_score.py
@brief  UC4: Chain all 3 CAMARA signals into a single fraud risk score.
@detail NOT part of the CAMARA spec. This is a sandbox convenience endpoint
        that demonstrates how to combine SIM swap, number verification, and
        location verification for fraud detection.

@usage  POST /sandbox/fraud-score with phoneNumber and optional location.
"""

from fastapi import APIRouter, HTTPException, Depends, Request

from engine import SimulationEngine
from carriers import get_registry, CarrierProfile
from auth import get_claims, TokenClaims


router = APIRouter(tags=["UC4 — Chained fraud signals"])


def _resolve_carrier(claims: TokenClaims, phone: str) -> CarrierProfile:
    """
    @brief   Resolve carrier from claims or MSISDN prefix.
    @param   claims  Validated token claims.
    @param   phone   E.164 phone number.
    @return  CarrierProfile to use.
    """
    registry = get_registry()
    if claims.carrier_override:
        return registry.get(claims.carrier_override)
    return registry.auto_detect(phone)


def _extract_seed(request: Request) -> int | None:
    """
    @brief   Extract optional X-Seed header for deterministic simulation.
    @param   request  HTTP request.
    @return  Integer seed or None.
    """
    raw = request.headers.get("X-Seed")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@router.post("/sandbox/fraud-score")
async def fraud_score(
    request: Request,
    body: dict,
    claims: TokenClaims = Depends(get_claims),
):
    """
    @brief   UC4: Chain all 3 CAMARA signals into a single fraud score.
    @param   body    Request body with phoneNumber and optional location.
    @param   claims  Validated bearer token claims.
    @return  Dict with riskScore (0-100), riskLevel, riskFactors, signals.
    @note    NOT part of CAMARA spec. Sandbox-only convenience endpoint.
    """
    phone = body.get("phoneNumber", "")
    if not phone:
        raise HTTPException(status_code=400, detail="phoneNumber required")

    carrier = _resolve_carrier(claims, phone)
    engine = SimulationEngine(profile=carrier, seed=_extract_seed(request))

    sim_result = await engine.run("sim_swap", {"phoneNumber": phone, "maxAge": 24})
    num_result = await engine.run("number_verify", {"phoneNumber": phone})

    loc_body: dict = {
        "device": {"phoneNumber": phone},
        "area": {"areaType": "CIRCLE"},
    }
    loc = body.get("location", {})
    if loc:
        loc_body["area"]["center"] = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
        }
        loc_body["area"]["radius"] = loc.get("radiusMeters", 10000)
    loc_result = await engine.run("location_verification", loc_body)

    risk_score, risk_factors = _calculate_risk(sim_result, num_result, loc_result)

    return _build_fraud_response(
        phone,
        carrier,
        risk_score,
        risk_factors,
        sim_result,
        num_result,
        loc_result,
    )


def _calculate_risk(sim_result, num_result, loc_result):
    """
    @brief   Calculate fraud risk score from 3 CAMARA signals.
    @param   sim_result  SIM swap engine result.
    @param   num_result  Number verification engine result.
    @param   loc_result  Location verification engine result.
    @return  Tuple of (risk_score: int, risk_factors: list[str]).
    """
    risk_score = 0
    risk_factors: list[str] = []

    sim_swap_date = (
        sim_result.data.get("latestSimChange") if sim_result.success else None
    )
    if sim_swap_date:
        risk_score += 40
        risk_factors.append("SIM swapped within 24 hours")

    if num_result.success and not num_result.data.get(
        "devicePhoneNumberVerified", True
    ):
        risk_score += 30
        risk_factors.append("Phone number does not match device SIM")

    if loc_result.success and loc_result.data.get("verificationResult") == "FALSE":
        risk_score += 30
        risk_factors.append("Device not in expected location")

    return min(risk_score, 100), risk_factors


def _build_fraud_response(
    phone,
    carrier,
    risk_score,
    risk_factors,
    sim_result,
    num_result,
    loc_result,
):
    """
    @brief   Build the fraud score response dict.
    @return  Dict with riskScore, riskLevel, riskFactors, signals, _simulation.
    """
    return {
        "phoneNumber": phone,
        "carrier": carrier.display_name,
        "riskScore": risk_score,
        "riskLevel": (
            "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "LOW"
        ),
        "riskFactors": risk_factors,
        "signals": {
            "simSwap": (
                sim_result.data
                if sim_result.success
                else {"error": sim_result.error_code}
            ),
            "numberVerification": (
                num_result.data
                if num_result.success
                else {"error": num_result.error_code}
            ),
            "locationVerification": (
                loc_result.data
                if loc_result.success
                else {"error": loc_result.error_code}
            ),
        },
        "_simulation": {
            "carrier": carrier.display_name,
            "simulated": True,
        },
    }
