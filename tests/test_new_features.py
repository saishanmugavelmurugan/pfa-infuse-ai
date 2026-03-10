"""
Test Suite for HealthTrack Pro New Features - Iteration 12
Tests: MFA-integrated login, Wearable Platforms API, Advanced Forecasting, FHIR R4 API
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://qa-track-suite.preview.emergentagent.com"

# Test credentials
DOCTOR_EMAIL = "doctor.priya@infuse.demo"
DOCTOR_PASSWORD = "demo1234"


class TestAuth:
    """Test authentication endpoints including MFA-integrated login"""
    
    def test_health_check(self):
        """Test that API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: Health check - status: {data.get('status')}")
    
    def test_login_without_mfa(self):
        """Test standard login flow - should work without MFA code if MFA not enabled"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Check if response has either access_token or mfa_required flag
        has_token = "access_token" in data
        has_mfa_flag = "mfa_required" in data
        
        assert has_token or has_mfa_flag, "Response should have access_token or mfa_required"
        
        if data.get("mfa_required"):
            print(f"PASS: Login returns mfa_required=True (MFA enabled for user)")
            assert "user_id" in data, "MFA response should include user_id"
        else:
            print(f"PASS: Login successful with access_token")
            assert data.get("access_token") is not None, "Should have access_token"
        
        return data
    
    def test_login_returns_mfa_enabled_status(self):
        """Verify login response indicates mfa_enabled status in user object"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Check if user object has mfa_enabled field
        if data.get("user"):
            assert "mfa_enabled" in data["user"], "User object should have mfa_enabled field"
            print(f"PASS: User mfa_enabled status = {data['user']['mfa_enabled']}")
        elif data.get("mfa_required"):
            print("PASS: MFA is required - user has MFA enabled")


class TestWearablesAPI:
    """Test wearable health integration endpoints"""
    
    def test_get_supported_platforms(self):
        """Test GET /api/wearables/platforms - list supported platforms"""
        response = requests.get(f"{BASE_URL}/api/wearables/platforms")
        assert response.status_code == 200, f"Failed to get platforms: {response.text}"
        data = response.json()
        
        assert "platforms" in data, "Response should have platforms list"
        platforms = data["platforms"]
        assert len(platforms) >= 2, "Should have at least 2 platforms (Apple Health, Google Fit)"
        
        # Verify expected platforms
        platform_ids = [p["id"] for p in platforms]
        assert "apple_health" in platform_ids, "Should include Apple Health"
        assert "google_fit" in platform_ids, "Should include Google Fit"
        
        # Verify platform structure
        apple_health = next((p for p in platforms if p["id"] == "apple_health"), None)
        assert apple_health is not None
        assert "requires_app" in apple_health
        assert "supported_data_types" in apple_health
        
        print(f"PASS: Supported platforms: {platform_ids}")
    
    def test_get_connected_platforms_requires_auth(self):
        """Test GET /api/wearables/connected requires authentication"""
        response = requests.get(f"{BASE_URL}/api/wearables/connected")
        assert response.status_code == 401, f"Expected 401 unauthorized, got: {response.status_code}"
        print("PASS: Connected platforms endpoint requires authentication")
    
    def test_get_connected_platforms_with_auth(self):
        """Test GET /api/wearables/connected with valid auth token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # Skip if MFA required
        if login_data.get("mfa_required"):
            pytest.skip("MFA required for this test")
        
        token = login_data.get("access_token")
        assert token, "No access token received"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/wearables/connected", headers=headers)
        assert response.status_code == 200, f"Failed to get connected platforms: {response.text}"
        
        data = response.json()
        assert "platforms" in data, "Response should have platforms list"
        print(f"PASS: Connected platforms retrieved. Count: {len(data['platforms'])}")
    
    def test_apple_health_import_endpoint(self):
        """Test POST /api/wearables/apple-health/import requires auth"""
        # Test with sample Apple Health data (mock data)
        response = requests.post(f"{BASE_URL}/api/wearables/apple-health/import", json={
            "records": [
                {
                    "type": "HKQuantityTypeIdentifierHeartRate",
                    "value": 72,
                    "startDate": datetime.now().isoformat(),
                    "sourceName": "Test Device"
                }
            ],
            "export_date": datetime.now().isoformat(),
            "device_info": {"name": "iPhone Test"}
        })
        # Should require authentication
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
        print("PASS: Apple Health import endpoint requires authentication")


class TestAdvancedForecasting:
    """Test advanced forecasting API (Prophet/ARIMA ensemble)"""
    
    def test_basic_forecast_endpoint(self):
        """Test POST /api/ml-health/trend/forecast - basic forecasting"""
        # Generate sample historical data
        historical_data = []
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            historical_data.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": 70 + (i % 5) * 2  # Simulated heart rate data
            })
        
        response = requests.post(f"{BASE_URL}/api/ml-health/trend/forecast", json={
            "patient_id": "test-patient-123",
            "metric": "heart_rate",
            "historical_data": historical_data,
            "forecast_days": 7
        })
        assert response.status_code == 200, f"Forecast failed: {response.text}"
        data = response.json()
        
        assert "patient_id" in data
        assert "forecast_id" in data
        print(f"PASS: Basic forecast endpoint working. Forecast ID: {data.get('forecast_id')}")
    
    def test_advanced_forecast_endpoint(self):
        """Test POST /api/ml-health/trend/advanced-forecast - Prophet/ARIMA ensemble"""
        # Generate sample historical data with 30 days
        historical_data = []
        base_date = datetime.now() - timedelta(days=30)
        import random
        for i in range(30):
            historical_data.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": 72 + random.uniform(-5, 5)  # Heart rate with some variation
            })
        
        response = requests.post(f"{BASE_URL}/api/ml-health/trend/advanced-forecast", json={
            "patient_id": "test-patient-456",
            "metric": "heart_rate",
            "historical_data": historical_data,
            "forecast_days": 7
        })
        assert response.status_code == 200, f"Advanced forecast failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "forecast_id" in data, "Should have forecast_id"
        assert "model_used" in data, "Should indicate model used"
        
        # Check forecast data
        if "forecast" in data:
            forecast = data["forecast"]
            assert "dates" in forecast, "Forecast should have dates"
            assert "values" in forecast, "Forecast should have values"
            assert len(forecast["values"]) == 7, f"Should have 7 forecast values, got {len(forecast.get('values', []))}"
            
            # Check confidence intervals
            if "confidence_lower" in forecast and "confidence_upper" in forecast:
                print(f"PASS: Advanced forecast with confidence intervals")
        
        # Check analysis
        if "analysis" in data:
            analysis = data["analysis"]
            assert "trend_direction" in analysis, "Should have trend direction"
            print(f"PASS: Trend direction: {analysis.get('trend_direction')}")
        
        # Check recommendations
        if "recommendations" in data:
            assert isinstance(data["recommendations"], list)
            print(f"PASS: Recommendations provided: {len(data['recommendations'])}")
        
        print(f"PASS: Advanced forecast using model: {data.get('model_used')}")
    
    def test_advanced_forecast_with_insufficient_data(self):
        """Test advanced forecast with minimal data (should use fallback)"""
        historical_data = [
            {"date": "2026-02-01", "value": 70},
            {"date": "2026-02-02", "value": 72},
            {"date": "2026-02-03", "value": 71}
        ]
        
        response = requests.post(f"{BASE_URL}/api/ml-health/trend/advanced-forecast", json={
            "patient_id": "test-patient-789",
            "metric": "heart_rate",
            "historical_data": historical_data,
            "forecast_days": 3
        })
        assert response.status_code == 200, f"Forecast with minimal data failed: {response.text}"
        data = response.json()
        
        # Should work but may use simpler model
        assert "forecast_id" in data
        print(f"PASS: Forecast with minimal data - model used: {data.get('model_used', 'unknown')}")


class TestFHIRAPI:
    """Test FHIR R4 API endpoints for NABIDH compliance"""
    
    def test_fhir_health_check(self):
        """Test FHIR server health endpoint"""
        response = requests.get(f"{BASE_URL}/api/fhir/health")
        assert response.status_code == 200, f"FHIR health check failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "healthy"
        assert data.get("fhir_version") == "4.0.1"
        assert data.get("nabidh_compliant") == True
        print(f"PASS: FHIR health - version {data.get('fhir_version')}, NABIDH compliant: {data.get('nabidh_compliant')}")
    
    def test_fhir_metadata_capability_statement(self):
        """Test GET /api/fhir/metadata - CapabilityStatement"""
        response = requests.get(f"{BASE_URL}/api/fhir/metadata")
        assert response.status_code == 200, f"FHIR metadata failed: {response.text}"
        data = response.json()
        
        assert data.get("resourceType") == "CapabilityStatement"
        assert data.get("fhirVersion") == "4.0.1"
        assert data.get("status") == "active"
        
        # Check rest resources
        rest = data.get("rest", [])
        assert len(rest) > 0, "Should have REST resources"
        
        resources = rest[0].get("resource", [])
        resource_types = [r["type"] for r in resources]
        
        # Verify NABIDH required resources
        required_types = ["Patient", "Practitioner", "Encounter", "Observation", "MedicationRequest"]
        for rt in required_types:
            assert rt in resource_types, f"Missing required resource type: {rt}"
        
        print(f"PASS: FHIR CapabilityStatement with resources: {resource_types}")
    
    def test_fhir_patient_search_requires_auth(self):
        """Test that FHIR Patient search requires authentication"""
        response = requests.get(f"{BASE_URL}/api/fhir/Patient")
        assert response.status_code == 401, f"Expected 401, got: {response.status_code}"
        print("PASS: FHIR Patient search requires authentication")
    
    def test_fhir_patient_search_with_auth(self):
        """Test GET /api/fhir/Patient with authentication"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        if login_data.get("mfa_required"):
            pytest.skip("MFA required for this test")
        
        token = login_data.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/fhir/Patient", headers=headers)
        assert response.status_code == 200, f"FHIR Patient search failed: {response.text}"
        data = response.json()
        
        # Should return a Bundle
        assert data.get("resourceType") == "Bundle"
        assert data.get("type") == "searchset"
        print(f"PASS: FHIR Patient search returns Bundle with {len(data.get('entry', []))} entries")
    
    def test_fhir_practitioner_search(self):
        """Test GET /api/fhir/Practitioner - public endpoint"""
        response = requests.get(f"{BASE_URL}/api/fhir/Practitioner")
        # This should work without auth since it's doctor directory
        if response.status_code == 401:
            print("INFO: Practitioner search requires auth")
        else:
            assert response.status_code == 200, f"FHIR Practitioner search failed: {response.text}"
            data = response.json()
            assert data.get("resourceType") == "Bundle"
            print(f"PASS: FHIR Practitioner search returns Bundle")


class TestMLHealthStatus:
    """Test ML Health Analysis status and basic endpoints"""
    
    def test_ml_health_status(self):
        """Test GET /api/ml-health/status"""
        response = requests.get(f"{BASE_URL}/api/ml-health/status")
        assert response.status_code == 200, f"ML health status failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "operational"
        
        # Check components
        components = data.get("components", {})
        expected_components = ["prakriti_classifier", "anomaly_detector", "trend_forecaster", "data_fusion", "ayurveda_rag"]
        for comp in expected_components:
            assert components.get(comp) == "ready", f"Component {comp} not ready"
        
        print(f"PASS: ML Health status operational. Components: {list(components.keys())}")
    
    def test_prakriti_questionnaire(self):
        """Test GET /api/ml-health/questionnaire/prakriti"""
        response = requests.get(f"{BASE_URL}/api/ml-health/questionnaire/prakriti")
        assert response.status_code == 200, f"Prakriti questionnaire failed: {response.text}"
        data = response.json()
        
        assert "questionnaire" in data
        assert len(data["questionnaire"]) == 10, f"Should have 10 questions, got {len(data['questionnaire'])}"
        
        print(f"PASS: Prakriti questionnaire has {len(data['questionnaire'])} questions")
    
    def test_prakriti_assessment(self):
        """Test POST /api/ml-health/prakriti/assess"""
        # Sample Vata-dominant questionnaire answers
        questionnaire = {
            "body_frame": 1,  # Thin
            "skin_type": 1,  # Dry
            "appetite": 1,  # Irregular
            "digestion": 1,  # Irregular
            "sleep_pattern": 1,  # Light
            "stress_response": 1,  # Anxiety
            "climate_preference": 1,  # Warm
            "activity_level": 1,  # Very active
            "memory": 1,  # Quick to learn/forget
            "emotional_nature": 1  # Fearful
        }
        
        response = requests.post(f"{BASE_URL}/api/ml-health/prakriti/assess", json={
            "patient_id": "test-patient-prakriti",
            "questionnaire": questionnaire
        })
        assert response.status_code == 200, f"Prakriti assessment failed: {response.text}"
        data = response.json()
        
        assert "prakriti" in data
        assert "dominant_dosha" in data
        assert "recommendations" in data
        
        print(f"PASS: Prakriti assessment - Constitution: {data.get('prakriti')}, Dominant Dosha: {data.get('dominant_dosha')}")


class TestPreviousFeatures:
    """Regression tests for previous features"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get authentication token for tests"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        if login_response.status_code == 200:
            data = login_response.json()
            if not data.get("mfa_required"):
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = None
                self.headers = {}
        else:
            self.token = None
            self.headers = {}
    
    def test_add_patient(self):
        """Test patient creation endpoint"""
        if not self.token:
            pytest.skip("No auth token available (MFA required)")
        
        unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
        response = requests.post(f"{BASE_URL}/api/healthtrack/patients", json={
            "first_name": "TEST",
            "last_name": f"Patient{unique_id}",
            "email": f"test.patient.{unique_id}@example.com",
            "phone": f"+9180000{unique_id[-5:]}",
            "date_of_birth": "1990-01-15",
            "gender": "male"
        }, headers=self.headers)
        
        assert response.status_code in [200, 201], f"Patient creation failed: {response.text}"
        data = response.json()
        
        # Check for patient in response
        patient = data.get("patient", data)
        assert "id" in patient or "patient_id" in patient, "Should return patient with ID"
        print(f"PASS: Patient created successfully")
    
    def test_ml_health_analysis_integration(self):
        """Test comprehensive ML health analysis"""
        response = requests.post(f"{BASE_URL}/api/ml-health/comprehensive/analyze", json={
            "patient_id": "test-comprehensive",
            "patient_info": {
                "name": "Test Patient",
                "age": 35,
                "gender": "male"
            },
            "questionnaire": {
                "body_frame": 2,
                "skin_type": 2,
                "appetite": 2,
                "digestion": 2,
                "sleep_pattern": 2,
                "stress_response": 2,
                "climate_preference": 2,
                "activity_level": 2,
                "memory": 2,
                "emotional_nature": 2
            },
            "vitals": {
                "heart_rate": 72,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "spo2": 98
            }
        })
        assert response.status_code == 200, f"Comprehensive analysis failed: {response.text}"
        data = response.json()
        
        assert "analysis_id" in data
        assert "prakriti" in data or "anomaly_analysis" in data
        print(f"PASS: Comprehensive ML health analysis working")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
