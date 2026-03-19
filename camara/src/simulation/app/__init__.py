"""
src.simulation.app — CAMARA Canada Sandbox simulation package.

@brief  Root package for the Python/FastAPI CAMARA simulation server.
@detail Exposes CAMARA-spec endpoints backed by configurable Canadian
        carrier profiles (Rogers, Bell, Telus). No real carrier connection.

@usage  uvicorn src.simulation.app.main:app --port 8080
"""
