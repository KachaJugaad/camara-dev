"""
surfaces — CAMARA API surface implementations.

@brief  Each module implements one CAMARA API surface (SIM swap, number
        verification, device location) with validate_request() and
        build_response() functions.
@detail Surfaces are stateless. All carrier-specific behavior comes from
        the CarrierProfile injected by the engine.

@usage  from surfaces import sim_swap, location_verification
        errors = sim_swap.validate_request(payload)
        data = sim_swap.build_response(payload, rng, carrier)

@note   device_location.py is kept for backward compat but
        location_verification.py is the spec-compliant module.
"""
