"""
Health Check and Metrics Endpoints
"""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.monitoring import HealthChecker, MetricsCollector, structured_logger
from backend.database.session_manager import sessionmanager

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["Health & Monitoring"])


@health_router.get("/health")
async def healthcheck():
    """Basic health check"""
    structured_logger.info("health_check_requested")

    db_status = False
    try:
        with sessionmanager.session() as db:
            db.execute("SELECT 1")
            db_status = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = False

    return JSONResponse(
        status_code=(
            status.HTTP_200_OK if db_status else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content={
            "status": "ok" if db_status else "error",
            "database": "healthy" if db_status else "unhealthy",
        },
    )


@health_router.get("/health/detailed")
async def detailed_healthcheck():
    """Detailed health check with all dependencies"""
    structured_logger.info("detailed_health_check_requested")

    health_status = {}

    # Check database
    try:
        with sessionmanager.session() as db:
            health_status = HealthChecker.check_all(db)
    except Exception as e:
        structured_logger.error("health_check_failed", error=str(e))
        health_status = {"status": "error", "error": str(e)}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=health_status,
    )


@health_router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    structured_logger.info("metrics_requested")

    metrics = MetricsCollector.get_metrics()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=metrics,
    )


@health_router.post("/metrics/reset")
async def reset_metrics():
    """Reset application metrics"""
    structured_logger.info("metrics_reset_requested")

    MetricsCollector.reset()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "metrics_reset"},
    )
