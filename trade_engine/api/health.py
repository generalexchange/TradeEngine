"""Health check endpoints.

Provides health status for monitoring and load balancing.
"""

from typing import Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "trade-engine"}


@router.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check - verifies service is ready to accept traffic.

    In production, this should check:
    - Database connectivity
    - Broker connectivity
    - Portfolio service connectivity
    - Redis connectivity

    Returns:
        Readiness status
    """
    # Stub implementation
    # In production, perform actual health checks
    return {"status": "ready", "service": "trade-engine"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check - verifies service is alive.

    Returns:
        Liveness status
    """
    return {"status": "alive", "service": "trade-engine"}

