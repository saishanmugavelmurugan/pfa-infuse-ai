from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class DrugDatabase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    drug_name: str = Field(..., min_length=2, max_length=200)
    generic_name: str
    brand_names: List[str] = Field(default_factory=list)
    
    # Classification
    category: str  # Antibiotic, Painkiller, Antiviral, etc.
    therapeutic_class: str  # e.g., NSAIDs, Antibiotics
    controlled_substance: bool = Field(default=False)
    prescription_required: bool = Field(default=True)
    
    # Dosage information
    available_forms: List[str] = Field(default_factory=list)  # tablet, syrup, injection
    common_dosages: List[str] = Field(default_factory=list)  # 250mg, 500mg
    standard_instructions: str = Field(default="As directed by physician")
    
    # Safety information
    side_effects: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    drug_interactions: List[str] = Field(default_factory=list)
    pregnancy_category: Optional[str] = None  # A, B, C, D, X
    
    # USP: Transparent pricing
    price_range: Dict = Field(default_factory=dict)  # {min, max, currency}
    
    # Metadata
    manufacturer: Optional[str] = None
    country_of_origin: str = Field(default="India")
    approval_number: Optional[str] = None
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "drug_name": "Paracetamol",
                "generic_name": "Acetaminophen",
                "category": "Analgesic",
                "available_forms": ["tablet", "syrup"],
                "common_dosages": ["250mg", "500mg", "650mg"]
            }
        }
