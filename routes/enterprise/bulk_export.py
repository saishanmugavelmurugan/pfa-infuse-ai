"""
Enterprise Bulk Data Export
Supports: CSV, JSON, XML formats
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import csv
import io
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/api/enterprise/export", tags=["Enterprise Export"])

# Get database
from dependencies import get_database


# Models
class ExportRequest(BaseModel):
    data_type: str = Field(..., description="Type of data: patients, appointments, prescriptions, devices, scans, etc.")
    format: str = Field(default="csv", description="Export format: csv, json, xml")
    filters: Optional[Dict[str, Any]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    fields: Optional[List[str]] = None


class ExportJob(BaseModel):
    id: str
    data_type: str
    format: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    download_url: Optional[str] = None
    record_count: Optional[int] = None
    file_size: Optional[int] = None
    error: Optional[str] = None


# Supported data types and their collections
EXPORTABLE_DATA = {
    "patients": {"collection": "patients", "description": "Patient records"},
    "appointments": {"collection": "appointments", "description": "Appointment records"},
    "prescriptions": {"collection": "prescriptions", "description": "Prescription records"},
    "lab_tests": {"collection": "lab_tests", "description": "Lab test records"},
    "devices": {"collection": "devices", "description": "Registered devices"},
    "url_scans": {"collection": "url_scans", "description": "URL scan history"},
    "sms_analyses": {"collection": "sms_analyses", "description": "SMS analysis history"},
    "threat_logs": {"collection": "threat_logs", "description": "Threat detection logs"},
    "audit_logs": {"collection": "audit_logs", "description": "System audit logs"},
    "users": {"collection": "users", "description": "User accounts"},
    "webhooks": {"collection": "webhooks", "description": "Webhook configurations"},
    "iot_endpoints": {"collection": "iot_endpoints", "description": "IoT device endpoints"}
}


@router.get("/data-types")
async def get_exportable_data_types():
    """Get list of exportable data types"""
    return {
        "data_types": EXPORTABLE_DATA,
        "supported_formats": ["csv", "json", "xml"]
    }


@router.post("/create")
async def create_export_job(request: ExportRequest, background_tasks: BackgroundTasks, db=Depends(get_database)):
    """Create a new bulk export job"""
    if request.data_type not in EXPORTABLE_DATA:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data type. Supported: {list(EXPORTABLE_DATA.keys())}"
        )
    
    if request.format not in ["csv", "json", "xml"]:
        raise HTTPException(status_code=400, detail="Invalid format. Supported: csv, json, xml")
    
    job_id = str(uuid4())
    job = {
        "id": job_id,
        "data_type": request.data_type,
        "format": request.format,
        "filters": request.filters,
        "date_from": request.date_from,
        "date_to": request.date_to,
        "fields": request.fields,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "download_url": None,
        "record_count": None,
        "file_size": None,
        "error": None
    }
    
    await db.export_jobs.insert_one(job)
    
    # Process export in background
    background_tasks.add_task(process_export_job, job_id, request, db)
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "export.job.created",
        "resource_type": "export_job",
        "resource_id": job_id,
        "details": {"data_type": request.data_type, "format": request.format},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"job_id": job_id, "status": "pending", "message": "Export job created"}


async def process_export_job(job_id: str, request: ExportRequest, db):
    """Background task to process export"""
    try:
        # Update status to processing
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing"}}
        )
        
        # Get collection
        collection_name = EXPORTABLE_DATA[request.data_type]["collection"]
        collection = db[collection_name]
        
        # Build query
        query = request.filters or {}
        if request.date_from or request.date_to:
            date_query = {}
            if request.date_from:
                date_query["$gte"] = request.date_from
            if request.date_to:
                date_query["$lte"] = request.date_to
            query["created_at"] = date_query
        
        # Fetch data
        projection = {"_id": 0}
        if request.fields:
            projection = {field: 1 for field in request.fields}
            projection["_id"] = 0
        
        data = await collection.find(query, projection).to_list(100000)
        
        # Store export data
        await db.export_data.insert_one({
            "job_id": job_id,
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update job status
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "download_url": f"/api/enterprise/export/download/{job_id}",
                "record_count": len(data)
            }}
        )
        
    except Exception as e:
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )


@router.get("/jobs")
async def list_export_jobs(status: Optional[str] = None, limit: int = 50, db=Depends(get_database)):
    """List export jobs"""
    query = {}
    if status:
        query["status"] = status
    
    jobs = await db.export_jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_export_job(job_id: str, db=Depends(get_database)):
    """Get export job status"""
    job = await db.export_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job


@router.get("/download/{job_id}")
async def download_export(job_id: str, db=Depends(get_database)):
    """Download export file"""
    job = await db.export_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Export not ready. Status: {job['status']}")
    
    # Get export data
    export_data = await db.export_data.find_one({"job_id": job_id})
    if not export_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    data = export_data["data"]
    format_type = job["format"]
    data_type = job["data_type"]
    
    # Generate file based on format
    if format_type == "json":
        content = json.dumps(data, indent=2, default=str)
        media_type = "application/json"
        filename = f"{data_type}_export_{job_id[:8]}.json"
    
    elif format_type == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"{data_type}_export_{job_id[:8]}.csv"
    
    elif format_type == "xml":
        root = ET.Element("data")
        root.set("type", data_type)
        root.set("exported_at", datetime.now(timezone.utc).isoformat())
        
        for item in data:
            record = ET.SubElement(root, "record")
            for key, value in item.items():
                field = ET.SubElement(record, key)
                field.text = str(value) if value is not None else ""
        
        content = ET.tostring(root, encoding="unicode", method="xml")
        content = f'<?xml version="1.0" encoding="UTF-8"?>\n{content}'
        media_type = "application/xml"
        filename = f"{data_type}_export_{job_id[:8]}.xml"
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    # Log download audit
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "export.downloaded",
        "resource_type": "export_job",
        "resource_id": job_id,
        "details": {"format": format_type, "record_count": len(data)},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/jobs/{job_id}")
async def delete_export_job(job_id: str, db=Depends(get_database)):
    """Delete export job and associated data"""
    result = await db.export_jobs.delete_one({"id": job_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    # Delete export data
    await db.export_data.delete_one({"job_id": job_id})
    
    return {"message": "Export job deleted successfully"}


# Quick export endpoints for common data types
@router.get("/quick/patients")
async def quick_export_patients(format: str = "csv", db=Depends(get_database)):
    """Quick export patients data"""
    data = await db.patients.find({}, {"_id": 0}).to_list(10000)
    return await generate_quick_export(data, "patients", format)


@router.get("/quick/devices")
async def quick_export_devices(format: str = "csv", db=Depends(get_database)):
    """Quick export devices data"""
    data = await db.devices.find({}, {"_id": 0}).to_list(10000)
    return await generate_quick_export(data, "devices", format)


@router.get("/quick/audit-logs")
async def quick_export_audit_logs(format: str = "csv", days: int = 30, db=Depends(get_database)):
    """Quick export audit logs"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = await db.audit_logs.find(
        {"timestamp": {"$gte": date_from}},
        {"_id": 0}
    ).to_list(100000)
    return await generate_quick_export(data, "audit_logs", format)


async def generate_quick_export(data: List[Dict], data_type: str, format: str):
    """Generate quick export response"""
    if format == "json":
        return {"data": data, "count": len(data), "type": data_type}
    
    elif format == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={data_type}_export.csv"}
        )
    
    elif format == "xml":
        root = ET.Element("data")
        root.set("type", data_type)
        for item in data:
            record = ET.SubElement(root, "record")
            for key, value in item.items():
                field = ET.SubElement(record, key)
                field.text = str(value) if value is not None else ""
        content = ET.tostring(root, encoding="unicode", method="xml")
        return StreamingResponse(
            io.BytesIO(f'<?xml version="1.0"?>\n{content}'.encode()),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={data_type}_export.xml"}
        )
    
    raise HTTPException(status_code=400, detail="Invalid format")
