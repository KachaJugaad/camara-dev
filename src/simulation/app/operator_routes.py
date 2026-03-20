"""
operator_routes.py — Operator self-onboarding endpoints.

@file   operator_routes.py
@brief  UC6: 8-step wizard for carriers to register their CAMARA endpoints.
@detail Stores operator configurations in-memory. When an operator registers
        a real endpoint, the sandbox can passthrough to it instead of simulating.

@usage  POST /operator/register — start onboarding
        GET /operator/status/:id — check onboarding progress
"""

import uuid
import time

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/operator", tags=["UC6 — Operator onboarding"])

# In-memory operator store — replace with database in production
_OPERATORS: dict[str, dict] = {}


@router.post("/register")
async def start_onboarding(body: dict):
    """
    @brief   Start operator onboarding — step 1 of 8.
    @param   body  Dict with organizationName, contactEmail, carrierName.
    @return  Dict with operatorId and onboarding status.
    @raises  HTTPException(400) if required fields missing.
    """
    org = body.get("organizationName", "").strip()
    email = body.get("contactEmail", "").strip()
    carrier = body.get("carrierName", "").strip()

    if not org or not email or not carrier:
        raise HTTPException(
            status_code=400,
            detail="organizationName, contactEmail, carrierName required",
        )

    op_id = f"op-{uuid.uuid4().hex[:12]}"
    _OPERATORS[op_id] = {
        "operatorId": op_id,
        "organizationName": org,
        "contactEmail": email,
        "carrierName": carrier,
        "createdAt": time.time(),
        "currentStep": 1,
        "totalSteps": 8,
        "steps": _build_steps(),
        "config": {},
    }

    return {
        "operatorId": op_id,
        "status": "onboarding_started",
        "currentStep": 1,
        "totalSteps": 8,
        "nextAction": "Configure MSISDN ranges (POST /operator/{id}/step/2)",
    }


@router.get("/status/{operator_id}")
async def get_status(operator_id: str):
    """
    @brief   Get onboarding progress for an operator.
    @param   operator_id  The operator ID from registration.
    @return  Dict with current step, completion status, and config.
    """
    op = _OPERATORS.get(operator_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")

    completed = sum(1 for s in op["steps"] if s["completed"])
    return {
        "operatorId": operator_id,
        "organizationName": op["organizationName"],
        "carrierName": op["carrierName"],
        "currentStep": op["currentStep"],
        "totalSteps": 8,
        "completedSteps": completed,
        "steps": op["steps"],
        "config": op["config"],
    }


@router.post("/step/{operator_id}/{step_num}")
async def complete_step(operator_id: str, step_num: int, body: dict):
    """
    @brief   Complete a specific onboarding step with its configuration.
    @param   operator_id  The operator ID.
    @param   step_num     Step number (1-8).
    @param   body         Step-specific configuration data.
    @return  Dict with updated status and next action.
    """
    op = _OPERATORS.get(operator_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    if step_num < 1 or step_num > 8:
        raise HTTPException(status_code=400, detail="Step must be 1-8")

    step = op["steps"][step_num - 1]
    step["completed"] = True
    step["data"] = body
    op["config"].update(body)
    op["currentStep"] = min(step_num + 1, 8)

    all_done = all(s["completed"] for s in op["steps"])
    return {
        "operatorId": operator_id,
        "stepCompleted": step_num,
        "stepName": step["name"],
        "currentStep": op["currentStep"],
        "allComplete": all_done,
        "status": "onboarding_complete" if all_done else "in_progress",
    }


@router.get("/list")
async def list_operators():
    """
    @brief   List all registered operators.
    @return  List of operator summaries.
    """
    return [
        {
            "operatorId": op["operatorId"],
            "organizationName": op["organizationName"],
            "carrierName": op["carrierName"],
            "completedSteps": sum(1 for s in op["steps"] if s["completed"]),
            "totalSteps": 8,
        }
        for op in _OPERATORS.values()
    ]


_STEP_DEFS = [
    ("Account Registration", "Organization name, contact email, carrier identity"),
    ("MSISDN Ranges", "Define phone number prefix ranges for your network"),
    ("Latency Profile", "Set p50/p95/p99 latency targets for simulation"),
    ("Error Profile", "Configure error injection rates (timeout, unavailable)"),
    ("Feature Flags", "Enable/disable CAMARA surfaces (SIM swap, location, etc.)"),
    ("Endpoint Registration", "Register your real CAMARA endpoint URL for passthrough"),
    ("Test Verification", "Run conformance tests against your registered endpoint"),
    ("Publish", "Make your carrier profile available to sandbox developers"),
]


def _build_steps() -> list[dict]:
    """
    @brief   Build the 8-step onboarding checklist.
    @return  List of step dicts with name, description, completed flag.
    """
    return [
        {"step": i + 1, "name": name, "description": desc, "completed": i == 0}
        for i, (name, desc) in enumerate(_STEP_DEFS)
    ]
