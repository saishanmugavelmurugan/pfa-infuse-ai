"""
Test suite for AI Health Analysis features
Tests: Doctor analytics, Patient analysis, Bulk analysis, Specialization metrics
"""
import pytest
import requests
import os
import json

# Use environment URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qa-track-suite.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "ranjeetkoul@infuse.net.in"
TEST_PASSWORD = "Ranjeet$03"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Authenticated headers"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def test_patient_id(auth_headers):
    """Create a test patient for analysis"""
    response = requests.post(f"{BASE_URL}/api/healthtrack/patients", 
        headers=auth_headers,
        json={
            "first_name": "TEST_AIAnalysis",
            "last_name": "Patient",
            "date_of_birth": "1980-01-15",
            "gender": "male",
            "email": "test.ai.analysis@example.com",
            "phone": "+1999888777",
            "address": {
                "street": "456 AI St",
                "city": "Analytics City",
                "state": "AI",
                "postal_code": "54321"
            }
        }
    )
    if response.status_code in [200, 201]:
        return response.json().get("patient", {}).get("id")
    return "test_patient_123"


class TestDoctorAnalyticsAPI:
    """Tests for /api/ai/doctor-analytics endpoint"""
    
    def test_doctor_analytics_returns_correct_structure(self, auth_headers):
        """Test that doctor analytics returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/ai/doctor-analytics", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify all required fields are present
        required_fields = ["totalPatients", "highRisk", "mediumRisk", "lowRisk", 
                          "pendingReviews", "completedToday", "avgRiskScore"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            assert isinstance(data[field], (int, float)), f"Field {field} should be numeric"
    
    def test_doctor_analytics_values_are_reasonable(self, auth_headers):
        """Test that analytics values are within reasonable bounds"""
        response = requests.get(f"{BASE_URL}/api/ai/doctor-analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Risk score should be 0-100
        assert 0 <= data["avgRiskScore"] <= 100, "avgRiskScore should be 0-100"
        
        # Counts should be non-negative
        assert data["totalPatients"] >= 0
        assert data["highRisk"] >= 0
        assert data["mediumRisk"] >= 0
        assert data["lowRisk"] >= 0
    
    def test_doctor_analytics_without_auth_fails(self):
        """Test that unauthorized access is rejected"""
        response = requests.get(f"{BASE_URL}/api/ai/doctor-analytics")
        # Should return 401 or 403
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestPatientAnalysisAPI:
    """Tests for /api/ai/analyze-patient endpoint"""
    
    def test_analyze_patient_general_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with general specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "general"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "analysis_id" in data
        assert "patient_id" in data
        assert "specialization" in data
        assert "synopsis" in data
        assert "keyFindings" in data
        assert "riskScore" in data
        assert "riskLevel" in data
        assert "suggestedActions" in data
    
    def test_analyze_patient_cardiology_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with cardiology specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "cardiology"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["specialization"] == "cardiology"
        assert "riskScore" in data
        assert data["riskLevel"] in ["low", "medium", "high"]
    
    def test_analyze_patient_endocrinology_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with endocrinology specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "endocrinology"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["specialization"] == "endocrinology"
    
    def test_analyze_patient_neurology_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with neurology specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "neurology"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["specialization"] == "neurology"
    
    def test_analyze_patient_orthopedics_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with orthopedics specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "orthopedics"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["specialization"] == "orthopedics"
    
    def test_analyze_patient_pediatrics_specialization(self, auth_headers, test_patient_id):
        """Test patient analysis with pediatrics specialization"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "pediatrics"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["specialization"] == "pediatrics"
    
    def test_analyze_patient_risk_levels_valid(self, auth_headers, test_patient_id):
        """Test that risk levels are always valid"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "general"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Risk score should be 0-100
        assert 0 <= data["riskScore"] <= 100
        # Risk level should be one of low/medium/high
        assert data["riskLevel"] in ["low", "medium", "high"]
        # AI confidence should be reasonable
        assert 0 <= data["aiConfidence"] <= 100
    
    def test_analyze_patient_key_findings_structure(self, auth_headers, test_patient_id):
        """Test that key findings have correct structure"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "general"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Key findings should be a list
        assert isinstance(data["keyFindings"], list)
        
        # Each finding should have metric, value, status, trend
        for finding in data["keyFindings"]:
            assert "metric" in finding
            assert "value" in finding
            assert "status" in finding
            assert "trend" in finding


class TestBulkAnalyzeAPI:
    """Tests for /api/ai/bulk-analyze endpoint"""
    
    def test_bulk_analyze_single_patient(self, auth_headers, test_patient_id):
        """Test bulk analysis with single patient"""
        response = requests.post(f"{BASE_URL}/api/ai/bulk-analyze", 
            headers=auth_headers,
            json={
                "patient_ids": [test_patient_id],
                "specialization": "general"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analysis_id" in data
        assert "total_analyzed" in data
        assert data["total_analyzed"] == 1
        assert "summary" in data
        assert "results" in data
    
    def test_bulk_analyze_returns_summary_counts(self, auth_headers, test_patient_id):
        """Test that bulk analysis returns risk summary counts"""
        response = requests.post(f"{BASE_URL}/api/ai/bulk-analyze", 
            headers=auth_headers,
            json={
                "patient_ids": [test_patient_id, "another_patient_id"],
                "specialization": "cardiology"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Summary should have risk counts
        summary = data.get("summary", {})
        assert "high_risk" in summary
        assert "medium_risk" in summary
        assert "low_risk" in summary
    
    def test_bulk_analyze_empty_list(self, auth_headers):
        """Test bulk analysis with empty patient list"""
        response = requests.post(f"{BASE_URL}/api/ai/bulk-analyze", 
            headers=auth_headers,
            json={
                "patient_ids": [],
                "specialization": "general"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_analyzed"] == 0


class TestHealthRecommendationsAPI:
    """Tests for /api/ai/health-recommendations endpoint"""
    
    def test_health_recommendations_basic(self, auth_headers):
        """Test basic health recommendations"""
        response = requests.post(f"{BASE_URL}/api/ai/health-recommendations", 
            headers=auth_headers,
            json={
                "patient_id": "current",
                "age": 35,
                "gender": "male",
                "conditions": ["hypertension"],
                "symptoms": ["fatigue"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have recommendations
        assert "allopathic_recommendations" in data
        assert "ayurvedic_recommendations" in data
        assert "lifestyle_tips" in data
        assert "disclaimer" in data
    
    def test_health_recommendations_includes_disclaimer(self, auth_headers):
        """Test that health recommendations include medical disclaimer"""
        response = requests.post(f"{BASE_URL}/api/ai/health-recommendations", 
            headers=auth_headers,
            json={
                "patient_id": "current"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Disclaimer should be present and contain important warning
        assert "disclaimer" in data
        assert "medical" in data["disclaimer"].lower() or "healthcare" in data["disclaimer"].lower()


class TestLabReportAnalysisAPI:
    """Tests for /api/ai/analyze-lab-report endpoint"""
    
    def test_analyze_lab_report_cbc(self, auth_headers, test_patient_id):
        """Test CBC lab report analysis"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-lab-report", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "test_type": "CBC",
                "results": {
                    "hemoglobin": 14.5,
                    "rbc": 4.8,
                    "wbc": 7500,
                    "platelets": 250000
                },
                "reference_ranges": {
                    "hemoglobin": "12-17 g/dL",
                    "rbc": "4.5-5.5 million/uL",
                    "wbc": "4500-11000 /uL",
                    "platelets": "150000-400000 /uL"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis_type"] == "lab_report"
        assert "findings" in data
        assert "allopathic_recommendations" in data
        assert "ayurvedic_recommendations" in data
    
    def test_analyze_lab_report_lipid_panel(self, auth_headers, test_patient_id):
        """Test Lipid Panel lab report analysis"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-lab-report", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "test_type": "Lipid Panel",
                "results": {
                    "total_cholesterol": 220,
                    "ldl": 140,
                    "hdl": 45,
                    "triglycerides": 180
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestRiskAssessmentAPI:
    """Tests for /api/ai/risk-assessment endpoint"""
    
    def test_risk_assessment_low_risk_patient(self, auth_headers):
        """Test cardiovascular risk assessment for low-risk patient"""
        response = requests.post(f"{BASE_URL}/api/ai/risk-assessment", 
            headers=auth_headers,
            json={
                "patient_id": "test_low_risk",
                "age": 30,
                "gender": "female",
                "bmi": 22.0,
                "smoking": False,
                "diabetes": False,
                "hypertension": False,
                "family_history": [],
                "cholesterol_total": 180,
                "hdl": 60,
                "systolic_bp": 115
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "risk_score" in data
        assert "risk_category" in data
        assert data["risk_category"] in ["Low", "Low-Moderate"]
    
    def test_risk_assessment_high_risk_patient(self, auth_headers):
        """Test cardiovascular risk assessment for high-risk patient"""
        response = requests.post(f"{BASE_URL}/api/ai/risk-assessment", 
            headers=auth_headers,
            json={
                "patient_id": "test_high_risk",
                "age": 68,
                "gender": "male",
                "bmi": 32.0,
                "smoking": True,
                "diabetes": True,
                "hypertension": True,
                "family_history": ["heart_disease", "stroke"],
                "cholesterol_total": 260,
                "hdl": 35,
                "systolic_bp": 165
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["risk_score"] > 5  # Should have elevated risk
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0


class TestPatientAnalysesHistoryAPI:
    """Tests for /api/ai/analyses/{patient_id} endpoint"""
    
    def test_get_patient_analyses_history(self, auth_headers, test_patient_id):
        """Test retrieving patient analysis history"""
        # First create an analysis
        requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            headers=auth_headers,
            json={
                "patient_id": test_patient_id,
                "specialization": "general"
            }
        )
        
        # Then retrieve history
        response = requests.get(
            f"{BASE_URL}/api/ai/analyses/{test_patient_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "patient_id" in data
        assert "analyses" in data
        assert isinstance(data["analyses"], list)


class TestAPIAuthentication:
    """Tests for API authentication requirements"""
    
    def test_analyze_patient_requires_auth(self):
        """Test that analyze-patient requires authentication"""
        response = requests.post(f"{BASE_URL}/api/ai/analyze-patient", 
            json={
                "patient_id": "test123",
                "specialization": "general"
            }
        )
        assert response.status_code in [401, 403, 422]
    
    def test_bulk_analyze_requires_auth(self):
        """Test that bulk-analyze requires authentication"""
        response = requests.post(f"{BASE_URL}/api/ai/bulk-analyze", 
            json={
                "patient_ids": ["test123"],
                "specialization": "general"
            }
        )
        assert response.status_code in [401, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
