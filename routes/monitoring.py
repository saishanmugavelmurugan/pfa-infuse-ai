"""
HealthTrack Pro - Production Monitoring & Alerting System
Provides health metrics, alerting thresholds, and capacity planning
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import dependencies
import os
import psutil
import asyncio
from collections import defaultdict

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Metrics"])


# ========== Configuration ==========

class AlertThreshold(BaseModel):
    metric: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str


class CapacityMetrics(BaseModel):
    current_users: int
    max_concurrent_users: int
    utilization_percent: float
    headroom_percent: float
    recommendation: str


# Default alerting thresholds
ALERT_THRESHOLDS = {
    "api_response_time_p95": AlertThreshold(
        metric="api_response_time_p95",
        warning_threshold=1000,  # ms
        critical_threshold=3000,  # ms
        unit="milliseconds",
        description="95th percentile API response time"
    ),
    "api_response_time_p99": AlertThreshold(
        metric="api_response_time_p99",
        warning_threshold=2000,  # ms
        critical_threshold=5000,  # ms
        unit="milliseconds",
        description="99th percentile API response time"
    ),
    "error_rate": AlertThreshold(
        metric="error_rate",
        warning_threshold=1.0,  # %
        critical_threshold=5.0,  # %
        unit="percent",
        description="API error rate"
    ),
    "cpu_usage": AlertThreshold(
        metric="cpu_usage",
        warning_threshold=70,  # %
        critical_threshold=90,  # %
        unit="percent",
        description="CPU utilization"
    ),
    "memory_usage": AlertThreshold(
        metric="memory_usage",
        warning_threshold=75,  # %
        critical_threshold=90,  # %
        unit="percent",
        description="Memory utilization"
    ),
    "disk_usage": AlertThreshold(
        metric="disk_usage",
        warning_threshold=80,  # %
        critical_threshold=95,  # %
        unit="percent",
        description="Disk space utilization"
    ),
    "db_connection_pool": AlertThreshold(
        metric="db_connection_pool",
        warning_threshold=70,  # %
        critical_threshold=90,  # %
        unit="percent",
        description="Database connection pool utilization"
    ),
    "requests_per_second": AlertThreshold(
        metric="requests_per_second",
        warning_threshold=100,  # Lower bound warning
        critical_threshold=500,  # Capacity limit
        unit="requests/second",
        description="Request throughput"
    )
}

# In-memory metrics storage (would be Redis/Prometheus in production)
metrics_store = defaultdict(list)
request_metrics = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})


# ========== Metrics Collection ==========

async def record_request_metric(endpoint: str, response_time_ms: float, is_error: bool = False):
    """Record a request metric"""
    now = datetime.now(timezone.utc)
    metrics_store[endpoint].append({
        "timestamp": now.isoformat(),
        "response_time_ms": response_time_ms,
        "is_error": is_error
    })
    
    # Keep only last hour of data
    cutoff = now - timedelta(hours=1)
    metrics_store[endpoint] = [
        m for m in metrics_store[endpoint]
        if datetime.fromisoformat(m["timestamp"]) > cutoff
    ]
    
    # Update aggregates
    request_metrics[endpoint]["count"] += 1
    request_metrics[endpoint]["total_time"] += response_time_ms
    if is_error:
        request_metrics[endpoint]["errors"] += 1


# ========== API Endpoints ==========

@router.get("/health")
async def detailed_health_check():
    """Comprehensive health check with component status"""
    db = await dependencies.get_database()
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "components": {}
    }
    
    # Check MongoDB
    try:
        await db.command("ping")
        health_status["components"]["mongodb"] = {
            "status": "healthy",
            "latency_ms": 1  # Would measure actual latency
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # System resources
    health_status["components"]["system"] = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
    
    return health_status


@router.get("/metrics")
async def get_system_metrics():
    """Get current system metrics"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "load_avg": list(os.getloadavg()) if hasattr(os, 'getloadavg') else None
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        },
        "network": {
            "connections": len(psutil.net_connections())
        }
    }


@router.get("/metrics/api")
async def get_api_metrics():
    """Get API performance metrics"""
    now = datetime.now(timezone.utc)
    cutoff_1h = now - timedelta(hours=1)
    cutoff_5m = now - timedelta(minutes=5)
    
    # Aggregate metrics
    total_requests = 0
    total_errors = 0
    response_times = []
    
    for endpoint, metrics in metrics_store.items():
        recent = [m for m in metrics if datetime.fromisoformat(m["timestamp"]) > cutoff_1h]
        total_requests += len(recent)
        total_errors += sum(1 for m in recent if m["is_error"])
        response_times.extend([m["response_time_ms"] for m in recent])
    
    # Calculate percentiles
    response_times.sort()
    p50 = response_times[len(response_times) // 2] if response_times else 0
    p95 = response_times[int(len(response_times) * 0.95)] if response_times else 0
    p99 = response_times[int(len(response_times) * 0.99)] if response_times else 0
    
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "timestamp": now.isoformat(),
        "period": "last_1_hour",
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate_percent": round(error_rate, 2),
        "response_times_ms": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "avg": round(sum(response_times) / len(response_times), 2) if response_times else 0
        },
        "endpoints": dict(request_metrics)
    }


@router.get("/metrics/database")
async def get_database_metrics():
    """Get MongoDB database metrics"""
    db = await dependencies.get_database()
    
    try:
        # Get database stats
        stats = await db.command("dbStats")
        
        # Get collection counts
        collections = await db.list_collection_names()
        collection_stats = {}
        for coll in collections[:10]:  # Limit to 10 collections
            count = await db[coll].count_documents({})
            collection_stats[coll] = {"document_count": count}
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": stats.get("db"),
            "storage_size_mb": round(stats.get("storageSize", 0) / (1024**2), 2),
            "data_size_mb": round(stats.get("dataSize", 0) / (1024**2), 2),
            "index_size_mb": round(stats.get("indexSize", 0) / (1024**2), 2),
            "total_collections": stats.get("collections", 0),
            "total_indexes": stats.get("indexes", 0),
            "collections": collection_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database metrics: {str(e)}")


@router.get("/alerts/thresholds")
async def get_alert_thresholds():
    """Get current alerting thresholds"""
    return {
        "thresholds": {k: v.dict() for k, v in ALERT_THRESHOLDS.items()}
    }


@router.get("/alerts/current")
async def get_current_alerts():
    """Check current metrics against thresholds and return any alerts"""
    alerts = []
    
    # Get current metrics
    system_metrics = await get_system_metrics()
    api_metrics = await get_api_metrics()
    
    # Check CPU
    cpu_threshold = ALERT_THRESHOLDS["cpu_usage"]
    cpu_usage = system_metrics["cpu"]["percent"]
    if cpu_usage >= cpu_threshold.critical_threshold:
        alerts.append({
            "severity": "critical",
            "metric": "cpu_usage",
            "current_value": cpu_usage,
            "threshold": cpu_threshold.critical_threshold,
            "message": f"CPU usage is critically high: {cpu_usage}%"
        })
    elif cpu_usage >= cpu_threshold.warning_threshold:
        alerts.append({
            "severity": "warning",
            "metric": "cpu_usage",
            "current_value": cpu_usage,
            "threshold": cpu_threshold.warning_threshold,
            "message": f"CPU usage is elevated: {cpu_usage}%"
        })
    
    # Check Memory
    mem_threshold = ALERT_THRESHOLDS["memory_usage"]
    mem_usage = system_metrics["memory"]["percent"]
    if mem_usage >= mem_threshold.critical_threshold:
        alerts.append({
            "severity": "critical",
            "metric": "memory_usage",
            "current_value": mem_usage,
            "threshold": mem_threshold.critical_threshold,
            "message": f"Memory usage is critically high: {mem_usage}%"
        })
    elif mem_usage >= mem_threshold.warning_threshold:
        alerts.append({
            "severity": "warning",
            "metric": "memory_usage",
            "current_value": mem_usage,
            "threshold": mem_threshold.warning_threshold,
            "message": f"Memory usage is elevated: {mem_usage}%"
        })
    
    # Check Disk
    disk_threshold = ALERT_THRESHOLDS["disk_usage"]
    disk_usage = system_metrics["disk"]["percent"]
    if disk_usage >= disk_threshold.critical_threshold:
        alerts.append({
            "severity": "critical",
            "metric": "disk_usage",
            "current_value": disk_usage,
            "threshold": disk_threshold.critical_threshold,
            "message": f"Disk usage is critically high: {disk_usage}%"
        })
    elif disk_usage >= disk_threshold.warning_threshold:
        alerts.append({
            "severity": "warning",
            "metric": "disk_usage",
            "current_value": disk_usage,
            "threshold": disk_threshold.warning_threshold,
            "message": f"Disk usage is elevated: {disk_usage}%"
        })
    
    # Check Error Rate
    error_threshold = ALERT_THRESHOLDS["error_rate"]
    error_rate = api_metrics["error_rate_percent"]
    if error_rate >= error_threshold.critical_threshold:
        alerts.append({
            "severity": "critical",
            "metric": "error_rate",
            "current_value": error_rate,
            "threshold": error_threshold.critical_threshold,
            "message": f"API error rate is critically high: {error_rate}%"
        })
    elif error_rate >= error_threshold.warning_threshold:
        alerts.append({
            "severity": "warning",
            "metric": "error_rate",
            "current_value": error_rate,
            "threshold": error_threshold.warning_threshold,
            "message": f"API error rate is elevated: {error_rate}%"
        })
    
    # Check Response Time
    p95_threshold = ALERT_THRESHOLDS["api_response_time_p95"]
    p95_time = api_metrics["response_times_ms"]["p95"]
    if p95_time >= p95_threshold.critical_threshold:
        alerts.append({
            "severity": "critical",
            "metric": "api_response_time_p95",
            "current_value": p95_time,
            "threshold": p95_threshold.critical_threshold,
            "message": f"API P95 response time is critically slow: {p95_time}ms"
        })
    elif p95_time >= p95_threshold.warning_threshold:
        alerts.append({
            "severity": "warning",
            "metric": "api_response_time_p95",
            "current_value": p95_time,
            "threshold": p95_threshold.warning_threshold,
            "message": f"API P95 response time is elevated: {p95_time}ms"
        })
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_alerts": len(alerts),
        "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
        "warning_count": len([a for a in alerts if a["severity"] == "warning"]),
        "alerts": alerts,
        "status": "critical" if any(a["severity"] == "critical" for a in alerts) else (
            "warning" if alerts else "healthy"
        )
    }


@router.get("/capacity")
async def get_capacity_planning():
    """Get capacity planning metrics and recommendations"""
    db = await dependencies.get_database()
    
    # Current resource utilization
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Estimate current capacity
    # Assuming linear scaling based on resource usage
    current_load_factor = max(cpu_percent, memory.percent) / 100
    
    # Capacity estimates (these would be calibrated from load tests)
    estimated_max_rps = 200  # Requests per second capacity
    current_rps = sum(rm["count"] for rm in request_metrics.values()) / 3600  # Last hour averaged
    
    # User capacity (based on typical user generating 0.1 requests/second)
    requests_per_user_per_second = 0.1
    max_concurrent_users = int(estimated_max_rps / requests_per_user_per_second)
    current_users = int(current_rps / requests_per_user_per_second) if current_rps > 0 else 0
    
    utilization = (current_load_factor * 100)
    headroom = 100 - utilization
    
    # Generate recommendation
    if utilization > 80:
        recommendation = "SCALE UP: Consider adding more resources or horizontal scaling"
    elif utilization > 60:
        recommendation = "MONITOR: Approaching capacity limits, plan for scaling"
    elif utilization < 20:
        recommendation = "OPTIMIZE: Consider rightsizing to reduce costs"
    else:
        recommendation = "HEALTHY: Current capacity is well-matched to load"
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_utilization": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "overall_percent": round(utilization, 1)
        },
        "capacity": {
            "estimated_max_rps": estimated_max_rps,
            "current_rps": round(current_rps, 2),
            "max_concurrent_users": max_concurrent_users,
            "current_users": current_users,
            "utilization_percent": round(utilization, 1),
            "headroom_percent": round(headroom, 1)
        },
        "scaling": {
            "recommendation": recommendation,
            "time_to_capacity_at_growth_rate": "N/A",  # Would calculate based on historical growth
            "suggested_resources": {
                "cpu_cores": max(2, int(psutil.cpu_count() * (utilization / 50))),
                "memory_gb": max(2, int(memory.total / (1024**3) * (utilization / 50))),
                "replicas": max(1, int(utilization / 50))
            }
        },
        "cost_optimization": {
            "current_efficiency": f"{round(100 - headroom + 20, 0)}%" if headroom > 20 else "Optimal",
            "potential_savings": "N/A"  # Would calculate based on cloud pricing
        }
    }


@router.get("/performance/benchmark")
async def run_performance_benchmark():
    """Run a quick performance benchmark"""
    import time
    db = await dependencies.get_database()
    
    results = {}
    
    # MongoDB read benchmark
    start = time.time()
    for _ in range(100):
        await db.drugs.find_one({})
    results["mongodb_read_100"] = {
        "total_ms": round((time.time() - start) * 1000, 2),
        "avg_ms": round((time.time() - start) * 10, 2)  # 1000/100
    }
    
    # MongoDB write benchmark
    start = time.time()
    for i in range(10):
        await db.benchmark_test.insert_one({"test": i, "timestamp": datetime.now(timezone.utc)})
    results["mongodb_write_10"] = {
        "total_ms": round((time.time() - start) * 1000, 2),
        "avg_ms": round((time.time() - start) * 100, 2)
    }
    
    # Cleanup
    await db.benchmark_test.delete_many({})
    
    # CPU benchmark
    start = time.time()
    total = sum(i * i for i in range(100000))
    results["cpu_100k_ops"] = {
        "total_ms": round((time.time() - start) * 1000, 2)
    }
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmarks": results,
        "summary": {
            "mongodb_health": "good" if results["mongodb_read_100"]["avg_ms"] < 10 else "slow",
            "cpu_health": "good" if results["cpu_100k_ops"]["total_ms"] < 100 else "slow"
        }
    }
