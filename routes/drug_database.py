"""
Drug Database API - MongoDB-backed Implementation
Replaces in-memory storage with MongoDB for scalability and persistence
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import httpx
import dependencies

router = APIRouter(prefix="/healthtrack/drug-database", tags=["HealthTrack - Drug Database"])


class DrugInfo(BaseModel):
    id: str
    name: str
    generic_name: str
    brand_names: List[str]
    drug_class: str
    dosage_forms: List[str]
    strengths: List[str]
    indications: List[str]
    contraindications: List[str]
    side_effects: List[str]
    interactions: List[str]
    warnings: List[str]
    pregnancy_category: Optional[str] = None
    manufacturer: Optional[str] = None
    price_range: Optional[dict] = None
    source: str = "internal"


class DrugSearchResult(BaseModel):
    total: int
    drugs: List[DrugInfo]


class DrugInteraction(BaseModel):
    drug_1_id: str
    drug_1_name: str
    drug_2_id: str
    drug_2_name: str
    severity: str
    description: str
    recommendation: str


@router.get("/search")
async def search_drugs(
    query: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100)
):
    """Search drugs by name, generic name, brand name, or indication in MongoDB"""
    db = await dependencies.get_database()
    
    # Use text search if text index exists, otherwise regex
    try:
        # Try text search first (more efficient)
        cursor = db.drugs.find(
            {"$text": {"$search": query}},
            {"_id": 0, "score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        
        results = await cursor.to_list(limit)
        
        # If no text results, fall back to regex search
        if not results:
            raise Exception("No text results, trying regex")
            
    except Exception:
        # Fallback to regex search
        query_regex = {"$regex": query, "$options": "i"}
        cursor = db.drugs.find(
            {
                "$or": [
                    {"name": query_regex},
                    {"generic_name": query_regex},
                    {"brand_names": query_regex},
                    {"indications": query_regex}
                ]
            },
            {"_id": 0}
        ).limit(limit)
        
        results = await cursor.to_list(limit)
    
    # Add source field
    for drug in results:
        drug["source"] = "internal"
        drug.pop("score", None)  # Remove text search score if present
    
    return {
        "query": query,
        "total": len(results),
        "drugs": results
    }


@router.get("/drug/{drug_id}")
async def get_drug_details(drug_id: str):
    """Get detailed information about a specific drug from MongoDB"""
    db = await dependencies.get_database()
    
    drug = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    
    drug["source"] = "internal"
    return drug


@router.get("/interactions")
async def check_drug_interactions(
    drug_ids: str = Query(..., description="Comma-separated drug IDs")
):
    """Check for potential drug interactions using MongoDB"""
    db = await dependencies.get_database()
    
    ids = [d.strip() for d in drug_ids.split(",")]
    
    if len(ids) < 2:
        return {"interactions": [], "message": "Need at least 2 drugs to check interactions"}
    
    # Fetch selected drugs
    cursor = db.drugs.find({"id": {"$in": ids}}, {"_id": 0})
    selected_drugs = await cursor.to_list(100)
    
    if len(selected_drugs) < 2:
        return {"interactions": [], "message": "Could not find enough drugs"}
    
    # Check for predefined interactions in database
    db_interactions = []
    for i, id1 in enumerate(ids):
        for id2 in ids[i+1:]:
            # Check both directions
            interaction = await db.drug_interactions.find_one(
                {
                    "$or": [
                        {"drug_1_id": id1, "drug_2_id": id2},
                        {"drug_1_id": id2, "drug_2_id": id1}
                    ]
                },
                {"_id": 0}
            )
            if interaction:
                # Get drug names
                drug1 = next((d for d in selected_drugs if d["id"] == interaction["drug_1_id"]), None)
                drug2 = next((d for d in selected_drugs if d["id"] == interaction["drug_2_id"]), None)
                
                db_interactions.append({
                    "drug1": drug1["name"] if drug1 else interaction["drug_1_id"],
                    "drug2": drug2["name"] if drug2 else interaction["drug_2_id"],
                    "severity": interaction.get("severity", "moderate"),
                    "description": interaction.get("description", ""),
                    "recommendation": interaction.get("recommendation", "")
                })
    
    # Also check interaction keywords in drug data
    keyword_interactions = []
    for i, drug1 in enumerate(selected_drugs):
        for drug2 in selected_drugs[i+1:]:
            # Check if drug2 name appears in drug1's interactions
            for interaction in drug1.get("interactions", []):
                if (drug2["name"].lower() in interaction.lower() or 
                    drug2["generic_name"].lower() in interaction.lower()):
                    keyword_interactions.append({
                        "drug1": drug1["name"],
                        "drug2": drug2["name"],
                        "interaction": interaction,
                        "severity": "moderate",
                        "source": "drug_label"
                    })
            
            # Check reverse
            for interaction in drug2.get("interactions", []):
                if (drug1["name"].lower() in interaction.lower() or 
                    drug1["generic_name"].lower() in interaction.lower()):
                    keyword_interactions.append({
                        "drug1": drug2["name"],
                        "drug2": drug1["name"],
                        "interaction": interaction,
                        "severity": "moderate",
                        "source": "drug_label"
                    })
    
    all_interactions = db_interactions + keyword_interactions
    
    return {
        "drugs_checked": [d["name"] for d in selected_drugs],
        "interactions_found": len(all_interactions),
        "interactions": all_interactions
    }


@router.get("/by-indication/{indication}")
async def get_drugs_by_indication(indication: str):
    """Get drugs for a specific medical indication from MongoDB"""
    db = await dependencies.get_database()
    
    query_regex = {"$regex": indication, "$options": "i"}
    
    cursor = db.drugs.find(
        {"indications": query_regex},
        {"_id": 0, "id": 1, "name": 1, "generic_name": 1, "drug_class": 1}
    ).limit(50)
    
    results = await cursor.to_list(50)
    
    return {
        "indication": indication,
        "total": len(results),
        "drugs": results
    }


@router.get("/by-class/{drug_class}")
async def get_drugs_by_class(drug_class: str):
    """Get drugs by therapeutic class from MongoDB"""
    db = await dependencies.get_database()
    
    query_regex = {"$regex": drug_class, "$options": "i"}
    
    cursor = db.drugs.find(
        {"drug_class": query_regex},
        {"_id": 0}
    ).limit(50)
    
    results = await cursor.to_list(50)
    
    return {
        "drug_class": drug_class,
        "total": len(results),
        "drugs": results
    }


@router.get("/pregnancy-safe")
async def get_pregnancy_safe_drugs(
    category: str = Query("A", description="FDA pregnancy category (A, B, C, D, X)")
):
    """Get drugs by pregnancy safety category from MongoDB"""
    db = await dependencies.get_database()
    
    safe_categories = ["A", "B"] if category.upper() in ["A", "B"] else [category.upper()]
    
    cursor = db.drugs.find(
        {"pregnancy_category": {"$in": safe_categories}},
        {"_id": 0, "id": 1, "name": 1, "generic_name": 1, "pregnancy_category": 1}
    ).limit(100)
    
    results = await cursor.to_list(100)
    
    return {
        "category": category,
        "total": len(results),
        "drugs": results
    }


@router.get("/all")
async def get_all_drugs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    drug_class: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Get all drugs with pagination from MongoDB"""
    db = await dependencies.get_database()
    
    query = {}
    if drug_class:
        query["drug_class"] = {"$regex": drug_class, "$options": "i"}
    if is_active is not None:
        query["is_active"] = is_active
    
    total = await db.drugs.count_documents(query)
    
    cursor = db.drugs.find(query, {"_id": 0}).skip(skip).limit(limit).sort("name", 1)
    results = await cursor.to_list(limit)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "drugs": results
    }


@router.get("/stats")
async def get_drug_database_stats():
    """Get statistics about the drug database"""
    db = await dependencies.get_database()
    
    total_drugs = await db.drugs.count_documents({})
    total_interactions = await db.drug_interactions.count_documents({})
    
    # Get drug class distribution
    pipeline = [
        {"$group": {"_id": "$drug_class", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    class_distribution = await db.drugs.aggregate(pipeline).to_list(10)
    
    # Get pregnancy category distribution
    pipeline = [
        {"$match": {"pregnancy_category": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$pregnancy_category", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    pregnancy_distribution = await db.drugs.aggregate(pipeline).to_list(10)
    
    return {
        "total_drugs": total_drugs,
        "total_interactions": total_interactions,
        "drug_classes": [{"class": d["_id"], "count": d["count"]} for d in class_distribution],
        "pregnancy_categories": [{"category": d["_id"], "count": d["count"]} for d in pregnancy_distribution],
        "source": "mongodb",
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


# =====================================================
# OpenFDA Integration (unchanged - external API)
# =====================================================

OPENFDA_BASE_URL = "https://api.fda.gov/drug"


@router.get("/openfda/search")
async def search_openfda_drugs(
    query: str = Query(..., min_length=2, description="Drug name to search"),
    limit: int = Query(10, ge=1, le=25)
):
    """Search drugs from OpenFDA database"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_query = f'openfda.brand_name:"{query}" OR openfda.generic_name:"{query}"'
            response = await client.get(
                f"{OPENFDA_BASE_URL}/label.json",
                params={
                    "search": search_query,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("results", []):
                    openfda = item.get("openfda", {})
                    
                    drug_info = {
                        "id": f"fda-{openfda.get('spl_id', ['unknown'])[0] if openfda.get('spl_id') else 'unknown'}",
                        "name": openfda.get("brand_name", ["Unknown"])[0] if openfda.get("brand_name") else "Unknown",
                        "generic_name": openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
                        "brand_names": openfda.get("brand_name", []),
                        "drug_class": openfda.get("pharm_class_epc", ["Unknown"])[0] if openfda.get("pharm_class_epc") else "Unknown",
                        "manufacturer": openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
                        "route": openfda.get("route", ["Unknown"])[0] if openfda.get("route") else "Unknown",
                        "dosage_forms": openfda.get("dosage_form", []),
                        "indications": item.get("indications_and_usage", ["Not available"])[:3] if item.get("indications_and_usage") else [],
                        "warnings": item.get("warnings", ["Not available"])[:2] if item.get("warnings") else [],
                        "contraindications": item.get("contraindications", ["Not available"])[:3] if item.get("contraindications") else [],
                        "side_effects": item.get("adverse_reactions", ["Not available"])[:3] if item.get("adverse_reactions") else [],
                        "interactions": item.get("drug_interactions", ["Not available"])[:3] if item.get("drug_interactions") else [],
                        "source": "openfda"
                    }
                    results.append(drug_info)
                
                return {
                    "query": query,
                    "total": len(results),
                    "source": "openfda",
                    "drugs": results
                }
            
            elif response.status_code == 404:
                return {"query": query, "total": 0, "source": "openfda", "drugs": [], "message": "No results found"}
            
            else:
                raise HTTPException(status_code=response.status_code, detail="OpenFDA API error")
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenFDA API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching OpenFDA: {str(e)}")


@router.get("/openfda/adverse-events")
async def get_adverse_events(
    drug_name: str = Query(..., description="Drug name to search adverse events for"),
    limit: int = Query(10, ge=1, le=50)
):
    """Get adverse event reports for a drug from OpenFDA"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{OPENFDA_BASE_URL}/event.json",
                params={
                    "search": f'patient.drug.medicinalproduct:"{drug_name}"',
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                events = []
                
                for item in data.get("results", []):
                    event = {
                        "report_id": item.get("safetyreportid", "Unknown"),
                        "receive_date": item.get("receivedate", "Unknown"),
                        "serious": item.get("serious", "Unknown"),
                        "reactions": [r.get("reactionmeddrapt", "Unknown") for r in item.get("patient", {}).get("reaction", [])][:5],
                        "outcome": item.get("patient", {}).get("patientdeath", {}).get("patientdeathdate", "No death reported")
                    }
                    events.append(event)
                
                return {
                    "drug_name": drug_name,
                    "total_events": len(events),
                    "events": events
                }
            
            elif response.status_code == 404:
                return {"drug_name": drug_name, "total_events": 0, "events": [], "message": "No adverse events found"}
            
            else:
                raise HTTPException(status_code=response.status_code, detail="OpenFDA API error")
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenFDA API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching adverse events: {str(e)}")


@router.get("/combined-search")
async def combined_drug_search(
    query: str = Query(..., min_length=2),
    include_openfda: bool = Query(True, description="Include OpenFDA results"),
    limit: int = Query(20, ge=1, le=50)
):
    """Search both internal MongoDB database and OpenFDA for comprehensive results"""
    db = await dependencies.get_database()
    
    # Search internal MongoDB database
    query_regex = {"$regex": query, "$options": "i"}
    cursor = db.drugs.find(
        {
            "$or": [
                {"name": query_regex},
                {"generic_name": query_regex},
                {"brand_names": query_regex},
                {"indications": query_regex}
            ]
        },
        {"_id": 0}
    ).limit(limit)
    
    internal_results = await cursor.to_list(limit)
    for drug in internal_results:
        drug["source"] = "internal"
    
    results = {
        "query": query,
        "internal_results": {
            "total": len(internal_results),
            "drugs": internal_results
        }
    }
    
    # Optionally search OpenFDA
    if include_openfda:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_query = f'openfda.brand_name:"{query}" OR openfda.generic_name:"{query}"'
                response = await client.get(
                    f"{OPENFDA_BASE_URL}/label.json",
                    params={
                        "search": search_query,
                        "limit": min(limit, 10)
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    fda_results = []
                    
                    for item in data.get("results", []):
                        openfda = item.get("openfda", {})
                        drug_info = {
                            "id": f"fda-{openfda.get('spl_id', ['unknown'])[0] if openfda.get('spl_id') else 'unknown'}",
                            "name": openfda.get("brand_name", ["Unknown"])[0] if openfda.get("brand_name") else "Unknown",
                            "generic_name": openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
                            "drug_class": openfda.get("pharm_class_epc", ["Unknown"])[0] if openfda.get("pharm_class_epc") else "Unknown",
                            "manufacturer": openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
                            "source": "openfda"
                        }
                        fda_results.append(drug_info)
                    
                    results["openfda_results"] = {
                        "total": len(fda_results),
                        "drugs": fda_results
                    }
                else:
                    results["openfda_results"] = {"total": 0, "drugs": [], "error": "API error or no results"}
                    
        except Exception as e:
            results["openfda_results"] = {"total": 0, "drugs": [], "error": str(e)}
    
    return results
