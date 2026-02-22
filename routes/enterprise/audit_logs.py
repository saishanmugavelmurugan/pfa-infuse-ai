"""
Enhanced Enterprise Audit Logging
Comprehensive logging for compliance and security
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json

router = APIRouter(prefix="/api/enterprise/audit", tags=["Enterprise Audit"])

# Get database
from dependencies import get_database


# Audit Event Categories
AUDIT_CATEGORIES = {
    "authentication": {
        "events": ["login", "logout", "login_failed", "password_changed", "mfa_enabled", "mfa_disabled"],
        "description": "Authentication and access events"
    },
    "authorization": {
        "events": ["permission_granted", "permission_revoked", "role_assigned", "role_removed"],
        "description": "Authorization and permission changes"
    },
    "data_access": {
        "events": ["record_viewed", "record_created", "record_updated", "record_deleted", "export_requested"],
        "description": "Data access and modification events"
    },
    "security": {
        "events": ["threat_detected", "scan_performed", "vulnerability_found", "ip_blocked"],
        "description": "Security-related events"
    },
    "configuration": {
        "events": ["setting_changed", "integration_added", "integration_removed", "webhook_created"],
        "description": "System configuration changes"
    },
    "api": {
        "events": ["api_key_created", "api_key_revoked", "rate_limit_exceeded", "api_error"],
        "description": "API usage events"
    },
    "compliance": {
        "events": ["consent_given", "consent_revoked", "data_retention_applied", "gdpr_request"],
        "description": "Compliance-related events"
    }
}


# Models
class AuditLogEntry(BaseModel):
    event_type: str
    category: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = Field(default="info", description="Severity: info, warning, error, critical")
    outcome: str = Field(default="success", description="Outcome: success, failure, pending")


class AuditSearchQuery(BaseModel):
    event_types: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    severity: Optional[str] = None
    outcome: Optional[str] = None
    search_text: Optional[str] = None
    limit: int = 100
    offset: int = 0


@router.get("/categories")
async def get_audit_categories():
    """Get audit event categories"""
    return {
        "categories": AUDIT_CATEGORIES,
        "severity_levels": ["info", "warning", "error", "critical"],
        "outcomes": ["success", "failure", "pending"]
    }


@router.post("/log")
async def create_audit_log(entry: AuditLogEntry, request: Request, db=Depends(get_database)):
    """Create an audit log entry"""
    log_id = str(uuid4())
    
    # Auto-detect category if not provided
    category = entry.category
    if not category:
        for cat, data in AUDIT_CATEGORIES.items():
            if any(evt in entry.event_type for evt in data["events"]):
                category = cat
                break
    
    log_data = {
        "id": log_id,
        "event_type": entry.event_type,
        "category": category or "general",
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "user_id": entry.user_id,
        "user_email": entry.user_email,
        "ip_address": entry.ip_address or request.client.host,
        "user_agent": entry.user_agent or request.headers.get("user-agent"),
        "details": entry.details or {},
        "severity": entry.severity,
        "outcome": entry.outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "year_month": datetime.now(timezone.utc).strftime("%Y-%m")
    }
    
    await db.audit_logs.insert_one(log_data)
    
    return {"id": log_id, "message": "Audit log created"}


@router.post("/search")
async def search_audit_logs(query: AuditSearchQuery, db=Depends(get_database)):
    """Search audit logs with filters"""
    mongo_query = {}
    
    if query.event_types:
        mongo_query["event_type"] = {"$in": query.event_types}
    
    if query.categories:
        mongo_query["category"] = {"$in": query.categories}
    
    if query.user_id:
        mongo_query["user_id"] = query.user_id
    
    if query.resource_type:
        mongo_query["resource_type"] = query.resource_type
    
    if query.resource_id:
        mongo_query["resource_id"] = query.resource_id
    
    if query.ip_address:
        mongo_query["ip_address"] = query.ip_address
    
    if query.severity:
        mongo_query["severity"] = query.severity
    
    if query.outcome:
        mongo_query["outcome"] = query.outcome
    
    if query.date_from or query.date_to:
        date_query = {}
        if query.date_from:
            date_query["$gte"] = query.date_from
        if query.date_to:
            date_query["$lte"] = query.date_to
        mongo_query["timestamp"] = date_query
    
    if query.search_text:
        mongo_query["$or"] = [
            {"event_type": {"$regex": query.search_text, "$options": "i"}},
            {"user_email": {"$regex": query.search_text, "$options": "i"}},
            {"resource_type": {"$regex": query.search_text, "$options": "i"}}
        ]
    
    total = await db.audit_logs.count_documents(mongo_query)
    logs = await db.audit_logs.find(mongo_query, {"_id": 0}).sort("timestamp", -1).skip(query.offset).limit(query.limit).to_list(query.limit)
    
    return {
        "logs": logs,
        "total": total,
        "limit": query.limit,
        "offset": query.offset,
        "has_more": (query.offset + len(logs)) < total
    }


@router.get("/logs")
async def list_audit_logs(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    db=Depends(get_database)
):
    """List recent audit logs"""
    query = {}
    
    if category:
        query["category"] = category
    
    if severity:
        query["severity"] = severity
    
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query["timestamp"] = {"$gte": date_from}
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    return {"logs": logs, "total": len(logs), "days": days}


@router.get("/logs/{log_id}")
async def get_audit_log(log_id: str, db=Depends(get_database)):
    """Get specific audit log entry"""
    log = await db.audit_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log


@router.get("/summary")
async def get_audit_summary(days: int = 30, db=Depends(get_database)):
    """Get audit log summary statistics"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get total count
    total = await db.audit_logs.count_documents({"timestamp": {"$gte": date_from}})
    
    # Get counts by category
    category_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    category_counts = {}
    async for doc in db.audit_logs.aggregate(category_pipeline):
        category_counts[doc["_id"] or "uncategorized"] = doc["count"]
    
    # Get counts by severity
    severity_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severity_counts = {}
    async for doc in db.audit_logs.aggregate(severity_pipeline):
        severity_counts[doc["_id"] or "info"] = doc["count"]
    
    # Get counts by outcome
    outcome_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {"_id": "$outcome", "count": {"$sum": 1}}}
    ]
    outcome_counts = {}
    async for doc in db.audit_logs.aggregate(outcome_pipeline):
        outcome_counts[doc["_id"] or "success"] = doc["count"]
    
    # Get top events
    top_events_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_events = []
    async for doc in db.audit_logs.aggregate(top_events_pipeline):
        top_events.append({"event_type": doc["_id"], "count": doc["count"]})
    
    # Get recent critical/error events
    critical_logs = await db.audit_logs.find(
        {"timestamp": {"$gte": date_from}, "severity": {"$in": ["error", "critical"]}},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(10)
    
    return {
        "summary": {
            "period_days": days,
            "total_events": total,
            "by_category": category_counts,
            "by_severity": severity_counts,
            "by_outcome": outcome_counts,
            "top_events": top_events,
            "recent_critical": critical_logs
        }
    }


@router.get("/user/{user_id}")
async def get_user_audit_trail(user_id: str, days: int = 30, limit: int = 100, db=Depends(get_database)):
    """Get audit trail for a specific user"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    logs = await db.audit_logs.find(
        {"user_id": user_id, "timestamp": {"$gte": date_from}},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return {"user_id": user_id, "logs": logs, "total": len(logs), "days": days}


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    limit: int = 100,
    db=Depends(get_database)
):
    """Get audit trail for a specific resource"""
    logs = await db.audit_logs.find(
        {"resource_type": resource_type, "resource_id": resource_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "logs": logs,
        "total": len(logs)
    }


@router.post("/retention/apply")
async def apply_retention_policy(retention_days: int = 90, db=Depends(get_database)):
    """Apply data retention policy to audit logs"""
    if retention_days < 30:
        raise HTTPException(status_code=400, detail="Minimum retention period is 30 days")
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    
    # Archive old logs before deletion (optional - store in archive collection)
    old_logs = await db.audit_logs.find({"timestamp": {"$lt": cutoff_date}}).to_list(None)
    if old_logs:
        await db.audit_logs_archive.insert_many(old_logs)
    
    # Delete old logs
    result = await db.audit_logs.delete_many({"timestamp": {"$lt": cutoff_date}})
    
    # Log this action
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "audit.retention.applied",
        "category": "compliance",
        "details": {
            "retention_days": retention_days,
            "deleted_count": result.deleted_count,
            "archived_count": len(old_logs)
        },
        "severity": "info",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Retention policy applied",
        "deleted_count": result.deleted_count,
        "archived_count": len(old_logs),
        "retention_days": retention_days
    }
