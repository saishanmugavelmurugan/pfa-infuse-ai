"""
ML Health Analysis API Tests
Tests for Prakriti classification, anomaly detection, trend forecasting, and report generation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMLHealthStatus:
    """Test ML Health system status endpoint"""
    
    def test_ml_health_status(self):
        """Test /api/ml-health/status endpoint"""
        response = requests.get(f"{BASE_URL}/api/ml-health/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify status is operational
        assert data["status"] == "operational"
        
        # Verify all components are ready
        assert data["components"]["prakriti_classifier"] == "ready"
        assert data["components"]["anomaly_detector"] == "ready"
        assert data["components"]["trend_forecaster"] == "ready"
        assert data["components"]["data_fusion"] == "ready"
        assert data["components"]["ayurveda_rag"] == "ready"
        assert data["components"]["report_generator"] == "ready"
        
        # Verify model accuracy info
        assert "85%+" in data["model_accuracy"]["prakriti_classification"]
        assert "90%+" in data["model_accuracy"]["anomaly_detection"]


class TestPrakritiQuestionnaire:
    """Test Prakriti questionnaire retrieval"""
    
    def test_get_prakriti_questionnaire(self):
        """Test GET /api/ml-health/questionnaire/prakriti"""
        response = requests.get(f"{BASE_URL}/api/ml-health/questionnaire/prakriti")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify questionnaire has 10 questions
        assert "questionnaire" in data
        assert len(data["questionnaire"]) == 10
        
        # Verify each question has required fields
        for question in data["questionnaire"]:
            assert "id" in question
            assert "question" in question
            assert "options" in question
            assert len(question["options"]) == 3  # Each question has 3 options
        
        # Verify instructions are present
        assert "instructions" in data


class TestPrakritiAssessment:
    """Test Prakriti constitution assessment API"""
    
    def test_prakriti_assessment_vata_dominant(self):
        """Test Prakriti assessment with Vata-dominant answers"""
        payload = {
            "patient_id": "test-vata-user",
            "questionnaire": {
                "body_frame": 1,
                "skin_type": 1,
                "appetite": 1,
                "digestion": 1,
                "sleep_pattern": 1,
                "stress_response": 1,
                "climate_preference": 1,
                "activity_level": 1,
                "memory": 1,
                "emotional_nature": 1
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/prakriti/assess",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["patient_id"] == "test-vata-user"
        assert "assessment_id" in data
        assert "prakriti" in data
        assert "confidence" in data
        assert "dosha_breakdown" in data
        assert "dominant_dosha" in data
        assert "secondary_dosha" in data
        assert "recommendations" in data
        
        # With all Vata (1) answers, dominant dosha should be Vata
        assert data["dominant_dosha"] == "Vata"
        assert data["dosha_breakdown"]["Vata"] >= 50
        
        # Verify recommendations structure
        recs = data["recommendations"]
        assert "diet" in recs
        assert "lifestyle" in recs
        assert "herbs" in recs
        assert "yoga" in recs
        assert "avoid" in recs
    
    def test_prakriti_assessment_pitta_dominant(self):
        """Test Prakriti assessment with Pitta-dominant answers"""
        payload = {
            "patient_id": "test-pitta-user",
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
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/prakriti/assess",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With all Pitta (2) answers, dominant dosha should be Pitta
        assert data["dominant_dosha"] == "Pitta"
        assert data["dosha_breakdown"]["Pitta"] >= 50
    
    def test_prakriti_assessment_kapha_dominant(self):
        """Test Prakriti assessment with Kapha-dominant answers"""
        payload = {
            "patient_id": "test-kapha-user",
            "questionnaire": {
                "body_frame": 3,
                "skin_type": 3,
                "appetite": 3,
                "digestion": 3,
                "sleep_pattern": 3,
                "stress_response": 3,
                "climate_preference": 3,
                "activity_level": 3,
                "memory": 3,
                "emotional_nature": 3
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/prakriti/assess",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With all Kapha (3) answers, dominant dosha should be Kapha
        assert data["dominant_dosha"] == "Kapha"
        assert data["dosha_breakdown"]["Kapha"] >= 50
    
    def test_prakriti_assessment_with_biometrics(self):
        """Test Prakriti assessment with optional biometrics"""
        payload = {
            "patient_id": "test-biometrics-user",
            "questionnaire": {
                "body_frame": 2,
                "skin_type": 1,
                "appetite": 2,
                "digestion": 1,
                "sleep_pattern": 1,
                "stress_response": 1,
                "climate_preference": 2,
                "activity_level": 1,
                "memory": 2,
                "emotional_nature": 1
            },
            "biometrics": {
                "bmi": 22.5,
                "resting_heart_rate": 72,
                "sleep_hours_avg": 7
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/prakriti/assess",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return valid assessment
        assert "prakriti" in data
        assert "confidence" in data
        assert data["confidence"] > 0


class TestAnomalyDetection:
    """Test health anomaly detection API"""
    
    def test_anomaly_detection_normal_vitals(self):
        """Test anomaly detection with normal vitals"""
        payload = {
            "patient_id": "test-normal-vitals",
            "current_vitals": {
                "heart_rate": 78,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "spo2": 98,
                "temperature": 36.6
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/anomaly/detect",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["patient_id"] == "test-normal-vitals"
        assert "analysis_id" in data
        assert "status" in data
        assert "critical_alerts" in data
        assert "warnings" in data
        assert "recommendations" in data
        
        # With normal vitals, status should be normal
        assert data["status"] == "normal"
        assert len(data["critical_alerts"]) == 0
    
    def test_anomaly_detection_high_heart_rate(self):
        """Test anomaly detection with high heart rate"""
        payload = {
            "patient_id": "test-high-hr",
            "current_vitals": {
                "heart_rate": 150,  # Above normal range
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "spo2": 98
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/anomaly/detect",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect warning for high heart rate
        assert data["status"] in ["warning", "critical"]
        assert len(data["warnings"]) > 0 or len(data["critical_alerts"]) > 0
    
    def test_anomaly_detection_low_spo2(self):
        """Test anomaly detection with critically low SpO2"""
        payload = {
            "patient_id": "test-low-spo2",
            "current_vitals": {
                "heart_rate": 80,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "spo2": 88  # Below normal
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/anomaly/detect",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect warning or critical for low SpO2
        assert data["status"] in ["warning", "critical"]


class TestTrendForecasting:
    """Test health trend forecasting API"""
    
    def test_trend_forecast_heart_rate(self):
        """Test trend forecasting for heart rate"""
        payload = {
            "patient_id": "test-trend-user",
            "metric": "heart_rate",
            "historical_data": [
                {"date": "2026-01-15", "value": 72},
                {"date": "2026-01-16", "value": 74},
                {"date": "2026-01-17", "value": 76},
                {"date": "2026-01-18", "value": 75},
                {"date": "2026-01-19", "value": 78},
                {"date": "2026-01-20", "value": 80},
                {"date": "2026-01-21", "value": 79}
            ],
            "forecast_days": 7
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/trend/forecast",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["patient_id"] == "test-trend-user"
        assert "forecast_id" in data
        assert data["metric"] == "heart_rate"
        assert "trend_direction" in data
        assert data["trend_direction"] in ["increasing", "decreasing", "stable"]
        assert "current_value" in data
        assert "mean_value" in data
        assert "forecast" in data
        assert "insights" in data
        
        # Verify forecast has correct number of days
        assert len(data["forecast"]) == 7
        
        # Verify each forecast point has required fields
        for point in data["forecast"]:
            assert "date" in point
            assert "predicted_value" in point
    
    def test_trend_forecast_insufficient_data(self):
        """Test trend forecasting with insufficient data"""
        payload = {
            "patient_id": "test-insufficient-data",
            "metric": "heart_rate",
            "historical_data": [
                {"date": "2026-01-20", "value": 80},
                {"date": "2026-01-21", "value": 82}
            ],
            "forecast_days": 7
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/trend/forecast",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return status indicating insufficient data
        assert data["status"] == "insufficient_data"


class TestDataFusion:
    """Test multimodal data fusion API"""
    
    def test_data_fusion_multiple_sources(self):
        """Test data fusion with multiple data sources"""
        payload = {
            "patient_id": "test-fusion-user",
            "lab_data": {
                "blood_glucose": 95,
                "cholesterol": 180
            },
            "wearable_data": {
                "heart_rate": 78,
                "steps": 8500
            },
            "user_data": {
                "sleep_hours": 7.5
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/data/fuse",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["patient_id"] == "test-fusion-user"
        assert "fusion_id" in data
        assert "sources_used" in data
        assert "fused_metrics" in data
        assert "confidence_score" in data
        assert "data_quality" in data
        
        # Verify sources are tracked
        assert "lab_report" in data["sources_used"]
        assert "wearable" in data["sources_used"]
        assert "user_input" in data["sources_used"]


class TestAyurvedaRemedies:
    """Test Ayurveda remedy retrieval API"""
    
    def test_ayurveda_remedy(self):
        """Test Ayurveda remedy for a condition"""
        payload = {
            "condition": "stress",
            "dosha": "Vata",
            "symptoms": ["anxiety", "insomnia"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/ayurveda/remedy",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["condition"] == "stress"
        assert data["dosha"] == "Vata"
        assert "remedy" in data
        assert "yoga_recommendations" in data
        assert "diet_guidelines" in data
    
    def test_get_herb_info(self):
        """Test herb information retrieval"""
        response = requests.get(f"{BASE_URL}/api/ml-health/ayurveda/herb/ashwagandha")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["herb"] == "ashwagandha"
        assert "info" in data


class TestComprehensiveAnalysis:
    """Test comprehensive health analysis API"""
    
    def test_comprehensive_analysis(self):
        """Test full comprehensive health analysis"""
        payload = {
            "patient_id": "test-comprehensive",
            "patient_info": {
                "name": "Test User",
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
                "heart_rate": 78,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80
            },
            "conditions": ["stress"],
            "symptoms": ["fatigue"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/comprehensive/analyze",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response contains all analysis components
        assert data["patient_id"] == "test-comprehensive"
        assert "analysis_id" in data
        assert "prakriti" in data  # Prakriti assessment included
        assert "anomaly_analysis" in data  # Anomaly detection included
        assert "fused_data" in data  # Data fusion included
        assert "summary" in data


class TestReportGeneration:
    """Test health report generation API"""
    
    def test_report_generation(self):
        """Test PDF health report generation"""
        payload = {
            "patient_id": "test-report-user",
            "patient_info": {
                "name": "Test User",
                "age": 35,
                "gender": "male",
                "report_id": "TEST-RPT-001"
            },
            "health_data": {
                "summary": {
                    "overall_status": "good",
                    "text": "Overall health is good",
                    "findings": ["All vitals normal"]
                },
                "vitals": {
                    "heart_rate": 78,
                    "blood_pressure": "120/80"
                },
                "lifestyle_tips": [
                    "Stay hydrated",
                    "Exercise regularly"
                ]
            },
            "language": "en"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ml-health/report/generate",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] == True
        assert "report_id" in data
        assert "download_url" in data
        assert "file_size" in data
        assert data["language"] == "en"


# Fixtures
@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
