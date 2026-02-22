from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/healthtrack/drugs", tags=["HealthTrack - Drug Database"])

@router.get("/search")
async def search_drugs(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search drugs - USP: Transparent pricing"""
    # Search in drug name, generic name, and brand names
    drugs = await db.drug_database.find(
        {
            "$or": [
                {"drug_name": {"$regex": q, "$options": "i"}},
                {"generic_name": {"$regex": q, "$options": "i"}},
                {"brand_names": {"$regex": q, "$options": "i"}}
            ],
            "is_active": True
        },
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {"query": q, "total": len(drugs), "drugs": drugs}

@router.get("/{drug_id}")
async def get_drug_details(
    drug_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed drug information"""
    drug = await db.drug_database.find_one(
        {"id": drug_id, "is_active": True},
        {"_id": 0}
    )
    
    if not drug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drug not found")
    
    return drug

@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_drug(
    drug_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add new drug to database - Admin only"""
    user_role = current_user.get("role")
    if user_role not in ["admin", "doctor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    drug_dict = {
        "id": str(uuid.uuid4()),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **drug_data
    }
    
    await db.drug_database.insert_one(drug_dict)
    drug_dict.pop("_id", None)
    
    return {"message": "Drug added successfully", "drug": drug_dict}

@router.get("/interactions/check")
async def check_drug_interactions(
    drug_ids: str = Query(..., description="Comma-separated drug IDs"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check for drug interactions"""
    drug_id_list = drug_ids.split(",")
    
    if len(drug_id_list) < 2:
        return {"interactions": [], "message": "Need at least 2 drugs to check interactions"}
    
    # Get all drugs
    drugs = await db.drug_database.find(
        {"id": {"$in": drug_id_list}, "is_active": True},
        {"_id": 0, "drug_name": 1, "drug_interactions": 1}
    ).to_list(len(drug_id_list))
    
    # Check for interactions
    interactions_found = []
    for i, drug1 in enumerate(drugs):
        for drug2 in drugs[i+1:]:
            if drug2["drug_name"] in drug1.get("drug_interactions", []):
                interactions_found.append({
                    "drug1": drug1["drug_name"],
                    "drug2": drug2["drug_name"],
                    "severity": "moderate",  # Simplified
                    "description": f"Potential interaction between {drug1['drug_name']} and {drug2['drug_name']}"
                })
    
    return {
        "total_drugs": len(drugs),
        "interactions_found": len(interactions_found),
        "interactions": interactions_found
    }
