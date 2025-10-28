"""
Application Performance Monitoring and Observability
"""

import logging
import time
from typing import Any, Dict
from functools import wraps
from contextlib import contextmanager
from fastapi import Request

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Track API performance metrics"""

    @staticmethod
    @contextmanager
    def track_time(operation: str):
        """Context manager to track execution time"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            logger.info(f"PERFORMANCE: {operation} took {duration:.4f}s")

    @staticmethod
    def track_api_metrics(request: Request, duration: float):
        """Track API endpoint metrics"""
        metrics = {
            "method": request.method,
            "path": request.url.path,
            "duration": duration,
            "status": "success",
        }
        logger.info(f"API METRICS: {metrics}")


def api_performance_monitor(func):
    """Decorator to monitor API endpoint performance"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time

            # Track performance
            logger.info(f"API {func.__name__} completed in {duration:.4f}s")

            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"API {func.__name__} failed after {duration:.4f}s: {e}")
            raise

    return wrapper


class StructuredLogger:
    """Structured JSON logging"""

    @staticmethod
    def info(event: str, **kwargs):
        """Log info with structured data"""
        log_data = {"event": event, **kwargs}
        logger.info(log_data)

    @staticmethod
    def error(event: str, **kwargs):
        """Log error with structured data"""
        log_data = {"event": event, **kwargs}
        logger.error(log_data)

    @staticmethod
    def warning(event: str, **kwargs):
        """Log warning with structured data"""
        log_data = {"event": event, **kwargs}
        logger.warning(log_data)


# Global structured logger
structured_logger = StructuredLogger()


class HealthChecker:
    """Health check for all dependencies"""

    @staticmethod
    def check_database(db_session) -> dict:
        """Check database health"""
        try:
            db_session.execute("SELECT 1")
            return {"status": "healthy"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def check_redis() -> dict:
        """Check Redis health"""
        try:
            from backend.core.cache import cache_manager

            if cache_manager.client:
                cache_manager.client.ping()
                return {"status": "healthy"}
            return {"status": "disabled"}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def check_all(db_session) -> dict:
        """Check all dependencies"""
        return {
            "database": HealthChecker.check_database(db_session),
            "cache": HealthChecker.check_redis(),
            "status": "ok",
        }


class MetricsCollector:
    """Collect application metrics"""

    metrics = {
        "api_calls": 0,
        "api_errors": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "db_queries": 0,
        "response_times": [],
    }

    @staticmethod
    def increment_api_calls():
        MetricsCollector.metrics["api_calls"] += 1

    @staticmethod
    def increment_api_errors():
        MetricsCollector.metrics["api_errors"] += 1

    @staticmethod
    def increment_cache_hit():
        MetricsCollector.metrics["cache_hits"] += 1

    @staticmethod
    def increment_cache_miss():
        MetricsCollector.metrics["cache_misses"] += 1

    @staticmethod
    def add_response_time(duration: float):
        MetricsCollector.metrics["response_times"].append(duration)
        # Keep only last 100 values
        if len(MetricsCollector.metrics["response_times"]) > 100:
            MetricsCollector.metrics["response_times"].pop(0)

    @staticmethod
    def get_metrics() -> dict:
        """Get current metrics"""
        response_times = MetricsCollector.metrics["response_times"]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        return {
            "api_calls": MetricsCollector.metrics["api_calls"],
            "api_errors": MetricsCollector.metrics["api_errors"],
            "cache_hits": MetricsCollector.metrics["cache_hits"],
            "cache_misses": MetricsCollector.metrics["cache_misses"],
            "cache_hit_rate": (
                MetricsCollector.metrics["cache_hits"]
                / (
                    MetricsCollector.metrics["cache_hits"]
                    + MetricsCollector.metrics["cache_misses"]
                )
                if (
                    MetricsCollector.metrics["cache_hits"]
                    + MetricsCollector.metrics["cache_misses"]
                )
                > 0
                else 0
            ),
            "avg_response_time": avg_response_time,
            "total_response_times": len(response_times),
        }

    @staticmethod
    def reset():
        """Reset metrics"""
        MetricsCollector.metrics = {
            "api_calls": 0,
            "api_errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "db_queries": 0,
            "response_times": [],
        }
