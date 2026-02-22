from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import random
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/lab-tests", tags=["HealthTrack - Lab Tests"])

def generate_order_number() -> str:
    return f"LAB-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

@router.get("/catalog")
async def get_lab_test_catalog(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get available lab tests catalog - USP: Transparent pricing"""
    query = {"is_active": True}
    
    if category:
        query["category"] = category
    
    if search:
        query["test_name"] = {"$regex": search, "$options": "i"}
    
    total = await db.lab_tests.count_documents(query)
    
    tests = await db.lab_tests.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "tests": tests}

@router.get("/catalog/{test_id}")
async def get_test_details(
    test_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed test information"""
    test = await db.lab_tests.find_one({"id": test_id, "is_active": True}, {"_id": 0})
    
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    
    return test

@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    order_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create lab test order - USP: Transparent pricing"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Calculate total amount
    total_amount = 0.0
    for test_item in order_data.get("tests", []):
        test = await db.lab_tests.find_one({"id": test_item["test_id"]}, {"_id": 0})
        if test:
            total_amount += test.get("price", 0)
    
    order_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "order_number": generate_order_number(),
        "order_date": datetime.now(timezone.utc).isoformat(),
        "status": "ordered",
        "total_amount": total_amount,
        "discount_applied": 0.0,
        "final_amount": total_amount,
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **order_data
    }
    
    await db.healthtrack_lab_orders.insert_one(order_dict)
    order_dict.pop("_id", None)
    
    return {"message": "Lab order created", "order": order_dict}

@router.get("/orders")
async def list_lab_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    patient_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List lab orders"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    if patient_id:
        query["patient_id"] = patient_id
    if status_filter:
        query["status"] = status_filter
    
    total = await db.healthtrack_lab_orders.count_documents(query)
    orders = await db.healthtrack_lab_orders.find(query, {"_id": 0}).sort("order_date", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "orders": orders}

@router.get("/orders/{order_id}")
async def get_lab_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get lab order details"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    order = await db.healthtrack_lab_orders.find_one({"id": order_id, "organization_id": org["id"]}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    return order

@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    new_status: str = Query(..., pattern=r'^(ordered|sample-collected|in-progress|completed|cancelled)$'),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update lab order status"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    update_data = {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}
    
    if new_status == "sample-collected":
        update_data["sample_collected_at"] = datetime.now(timezone.utc).isoformat()
    elif new_status == "completed":
        update_data["results_available_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.healthtrack_lab_orders.update_one(
        {"id": order_id, "organization_id": org["id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    return {"message": "Status updated", "new_status": new_status}

@router.post("/results", status_code=status.HTTP_201_CREATED)
async def upload_lab_results(
    results_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upload lab test results - USP: Encrypted storage"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    result_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "result_date": datetime.now(timezone.utc).isoformat(),
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **results_data
    }
    
    await db.healthtrack_lab_results.insert_one(result_dict)
    result_dict.pop("_id", None)
    
    return {"message": "Results uploaded", "result": result_dict}

@router.get("/results/patient/{patient_id}")
async def get_patient_lab_results(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all lab results for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    results = await db.healthtrack_lab_results.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("result_date", -1).to_list(100)
    
    return {"patient_id": patient_id, "total": len(results), "results": results}

@router.get("/tests/patient/{patient_id}")
async def get_patient_lab_tests(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all lab tests for a patient from healthtrack_lab_tests collection"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    lab_tests = await db.healthtrack_lab_tests.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("order_date", -1).to_list(100)
    
    return {"patient_id": patient_id, "total": len(lab_tests), "lab_tests": lab_tests}
