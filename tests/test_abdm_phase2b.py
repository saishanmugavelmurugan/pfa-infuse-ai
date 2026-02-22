#!/usr/bin/env python3
"""
Phase 2B ABDM Integration API Testing Suite
Tests the newly implemented Ayushman Bharat and National Health Records features.

Test Flow:
1. Login to get authentication token
2. Get a patient ID from existing patients
3. Test Ayushman Bharat Eligibility Check
4. Test Claims Submission (Pre-Auth)
5. Test Get Patient Claims
6. Test Claims Dashboard Summary
7. Test National Health Records Fetch (with consent flow)
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# External backend URL from frontend/.env
BACKEND_URL = "https://caretrack-68.preview.emergentagent.com/api"

class ABDMPhase2BTester:
    def __init__(self):
        self.session = None
        self.results = []
        self.token = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test result with detailed information"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success or (response_data and isinstance(response_data, dict)):
            print(f"   Details: {details}")
            if response_data:
                # Print key response fields for verification
                if isinstance(response_data, dict):
                    for key in ["is_eligible", "coverage_amount", "claim_number", "status", "records_count", "total_claims"]:
                        if key in response_data:
                            print(f"   {key}: {response_data[key]}")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def login_and_get_token(self):
        """Step 1: Login with doctor credentials"""
        try:
            url = f"{BACKEND_URL}/auth/login"
            login_data = {
                "email": "doctor.priya@infuse.demo",
                "password": "demo1234"
            }
            
            async with self.session.post(url, json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("access_token")
                    if self.token:
                        # Add Authorization header to session
                        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                        self.log_result("Login Authentication", True, "Successfully authenticated as doctor.priya@infuse.demo")
                        return True
                else:
                    error_text = await response.text()
                    self.log_result("Login Authentication", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Login Authentication", False, f"Exception: {str(e)}")
            return False
    
    async def get_patient_id(self):
        """Step 2: Get a patient ID from existing patients"""
        try:
            url = f"{BACKEND_URL}/healthtrack/patients"
            params = {"limit": 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    patients = data.get("patients", [])
                    if patients:
                        patient_id = patients[0].get("id")
                        patient_name = f"{patients[0].get('first_name', '')} {patients[0].get('last_name', '')}"
                        self.log_result("Get Patient ID", True, f"Found patient: {patient_name} (ID: {patient_id})")
                        return patient_id
                    else:
                        self.log_result("Get Patient ID", False, "No patients found in system")
                        return None
                else:
                    error_text = await response.text()
                    self.log_result("Get Patient ID", False, f"Status: {response.status}, Error: {error_text}")
                    return None
        except Exception as e:
            self.log_result("Get Patient ID", False, f"Exception: {str(e)}")
            return None
    
    async def test_ayushman_eligibility(self, patient_id):
        """Step 3: Test Ayushman Bharat Eligibility Check"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/ayushman/eligibility/check"
            request_data = {
                "patient_id": patient_id,
                "scheme": "PMJAY"
            }
            
            async with self.session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify expected response structure
                    required_keys = ["is_eligible", "eligibility_details", "covered_packages"]
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        self.log_result("Ayushman Bharat Eligibility Check", False, f"Missing keys: {missing_keys}", data)
                        return False
                    
                    # Verify eligibility details
                    eligibility_details = data.get("eligibility_details", {})
                    if eligibility_details.get("coverage_amount") != 500000:
                        self.log_result("Ayushman Bharat Eligibility Check", False, f"Expected coverage_amount=500000, got {eligibility_details.get('coverage_amount')}", data)
                        return False
                    
                    # Verify covered packages array exists
                    covered_packages = data.get("covered_packages", [])
                    if not isinstance(covered_packages, list) or len(covered_packages) == 0:
                        self.log_result("Ayushman Bharat Eligibility Check", False, "covered_packages should be non-empty array", data)
                        return False
                    
                    self.log_result("Ayushman Bharat Eligibility Check", True, f"Eligible: {data['is_eligible']}, Coverage: ₹{eligibility_details.get('coverage_amount', 0):,}", data)
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Ayushman Bharat Eligibility Check", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Ayushman Bharat Eligibility Check", False, f"Exception: {str(e)}")
            return False
    
    async def test_claims_submission(self, patient_id):
        """Step 4: Test Claims Submission (Pre-Auth)"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/ayushman/claims/submit"
            request_data = {
                "patient_id": patient_id,
                "abha_number": "91-1234-5678-9012",
                "claim_type": "preauth",
                "diagnosis_codes": ["I10"],
                "procedure_codes": ["99213"],
                "package_code": "HBP-01",
                "package_name": "General Medicine",
                "estimated_amount": 25000,
                "treatment_details": {"treatment_type": "OPD"}
            }
            
            async with self.session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify expected response structure
                    required_keys = ["success", "claim_number", "status"]
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        self.log_result("Claims Submission (Pre-Auth)", False, f"Missing keys: {missing_keys}", data)
                        return False, None
                    
                    # Verify preauth is auto-approved
                    if data.get("status") != "APPROVED":
                        self.log_result("Claims Submission (Pre-Auth)", False, f"Expected status=APPROVED for preauth, got {data.get('status')}", data)
                        return False, None
                    
                    claim_number = data.get("claim_number")
                    self.log_result("Claims Submission (Pre-Auth)", True, f"Claim submitted: {claim_number}, Status: {data['status']}", data)
                    return True, claim_number
                else:
                    error_text = await response.text()
                    self.log_result("Claims Submission (Pre-Auth)", False, f"Status: {response.status}, Error: {error_text}")
                    return False, None
        except Exception as e:
            self.log_result("Claims Submission (Pre-Auth)", False, f"Exception: {str(e)}")
            return False, None
    
    async def test_get_patient_claims(self, patient_id):
        """Step 5: Test Get Patient Claims"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/ayushman/claims/patient/{patient_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify expected response structure
                    required_keys = ["patient_id", "summary", "claims"]
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        self.log_result("Get Patient Claims", False, f"Missing keys: {missing_keys}", data)
                        return False
                    
                    claims = data.get("claims", [])
                    summary = data.get("summary", {})
                    
                    self.log_result("Get Patient Claims", True, f"Found {len(claims)} claims, Total estimated: ₹{summary.get('total_estimated', 0):,}", data)
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Get Patient Claims", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Get Patient Claims", False, f"Exception: {str(e)}")
            return False
    
    async def test_claims_dashboard(self):
        """Step 6: Test Claims Dashboard Summary"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/ayushman/claims/dashboard/summary"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify expected response structure
                    required_keys = ["total_claims", "total_estimated_amount", "total_approved_amount"]
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        self.log_result("Claims Dashboard Summary", False, f"Missing keys: {missing_keys}", data)
                        return False
                    
                    total_claims = data.get("total_claims", 0)
                    total_estimated = data.get("total_estimated_amount", 0)
                    total_approved = data.get("total_approved_amount", 0)
                    
                    self.log_result("Claims Dashboard Summary", True, f"Total claims: {total_claims}, Estimated: ₹{total_estimated:,}, Approved: ₹{total_approved:,}", data)
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Claims Dashboard Summary", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Claims Dashboard Summary", False, f"Exception: {str(e)}")
            return False
    
    async def test_national_health_records(self, patient_id):
        """Step 7: Test National Health Records Fetch (with consent flow)"""
        
        # First register an ABHA for testing
        abha_number = await self.register_test_abha()
        if not abha_number:
            return False
        
        # Link ABHA to patient
        if not await self.link_abha_to_patient(patient_id, abha_number):
            return False
        
        # Create consent request
        consent_id = await self.create_consent_request(patient_id)
        if not consent_id:
            return False
        
        # Approve consent
        if not await self.approve_consent(consent_id):
            return False
        
        # Fetch national health records
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/health-records/fetch"
            request_data = {
                "patient_id": patient_id,
                "abha_number": abha_number,
                "consent_id": consent_id,
                "hi_types": ["OPConsultation", "Prescription"]
            }
            
            async with self.session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify expected response structure
                    required_keys = ["fetch_id", "status", "records_count", "records"]
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        self.log_result("National Health Records Fetch", False, f"Missing keys: {missing_keys}", data)
                        return False
                    
                    records = data.get("records", [])
                    source_facilities = data.get("source_facilities", [])
                    
                    # Verify records from demo HIPs
                    expected_facilities = ["AIIMS Delhi", "Safdarjung Hospital", "Apollo Bangalore"]
                    for facility in expected_facilities:
                        if facility not in source_facilities:
                            self.log_result("National Health Records Fetch", False, f"Missing expected facility: {facility}", data)
                            return False
                    
                    self.log_result("National Health Records Fetch", True, f"Fetched {len(records)} records from {len(source_facilities)} facilities", data)
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("National Health Records Fetch", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("National Health Records Fetch", False, f"Exception: {str(e)}")
            return False
    
    async def register_test_abha(self):
        """Register a test ABHA for testing purposes"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/abha/register"
            abha_data = {
                "first_name": "Test",
                "last_name": "Patient",
                "date_of_birth": "1990-01-15",
                "gender": "M",
                "mobile": "9876543210",
                "email": "test.patient@example.com"
            }
            
            async with self.session.post(url, json=abha_data) as response:
                if response.status == 200:
                    data = await response.json()
                    abha_number = data.get("abha_number")
                    self.log_result("Register Test ABHA", True, f"ABHA Number: {abha_number}")
                    return abha_number
                else:
                    error_text = await response.text()
                    self.log_result("Register Test ABHA", False, f"Status: {response.status}, Error: {error_text}")
                    return None
        except Exception as e:
            self.log_result("Register Test ABHA", False, f"Exception: {str(e)}")
            return None
    
    async def link_abha_to_patient(self, patient_id, abha_number):
        """Link ABHA to patient"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/abha/link-patient"
            link_data = {
                "patient_id": patient_id,
                "abha_number": abha_number,
                "abha_address": f"test{abha_number[-4:]}@abdm"
            }
            
            async with self.session.post(url, json=link_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result("Link ABHA to Patient", True, f"Link ID: {data.get('link_id')}")
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Link ABHA to Patient", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Link ABHA to Patient", False, f"Exception: {str(e)}")
            return False
    
    async def create_consent_request(self, patient_id):
        """Create a consent request for health records access"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/consent/request"
            consent_data = {
                "patient_id": patient_id,
                "purpose": "CAREMGT",
                "hi_types": ["OPConsultation", "Prescription"],
                "date_range_from": "2024-01-01",
                "date_range_to": "2024-12-31",
                "requester_name": "Dr. Priya Sharma",
                "requester_type": "HIP"
            }
            
            async with self.session.post(url, json=consent_data) as response:
                if response.status == 200:
                    data = await response.json()
                    consent_id = data.get("consent_id")
                    self.log_result("Create Consent Request", True, f"Consent ID: {consent_id}")
                    return consent_id
                else:
                    error_text = await response.text()
                    self.log_result("Create Consent Request", False, f"Status: {response.status}, Error: {error_text}")
                    return None
        except Exception as e:
            self.log_result("Create Consent Request", False, f"Exception: {str(e)}")
            return None
    
    async def approve_consent(self, consent_id):
        """Approve a consent request"""
        try:
            url = f"{BACKEND_URL}/healthtrack/abdm/consent/{consent_id}/approve"
            
            async with self.session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result("Approve Consent", True, f"Status: {data.get('status')}")
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Approve Consent", False, f"Status: {response.status}, Error: {error_text}")
                    return False
        except Exception as e:
            self.log_result("Approve Consent", False, f"Exception: {str(e)}")
            return False
    
    async def run_phase2b_tests(self):
        """Run all Phase 2B ABDM Integration tests"""
        print("🚀 Starting Phase 2B ABDM Integration API Tests")
        print(f"🔗 Backend URL: {BACKEND_URL}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Step 1: Login
        print("\n📋 Step 1: Authentication")
        if not await self.login_and_get_token():
            return False
        
        # Step 2: Get Patient ID
        print("\n📋 Step 2: Get Patient ID")
        patient_id = await self.get_patient_id()
        if not patient_id:
            return False
        
        # Step 3: Test Ayushman Bharat Eligibility
        print("\n📋 Step 3: Ayushman Bharat Eligibility Check")
        if not await self.test_ayushman_eligibility(patient_id):
            return False
        
        # Step 4: Test Claims Submission
        print("\n📋 Step 4: Claims Submission (Pre-Auth)")
        success, claim_number = await self.test_claims_submission(patient_id)
        if not success:
            return False
        
        # Step 5: Test Get Patient Claims
        print("\n📋 Step 5: Get Patient Claims")
        if not await self.test_get_patient_claims(patient_id):
            return False
        
        # Step 6: Test Claims Dashboard
        print("\n📋 Step 6: Claims Dashboard Summary")
        if not await self.test_claims_dashboard():
            return False
        
        # Step 7: Test National Health Records
        print("\n📋 Step 7: National Health Records Fetch")
        if not await self.test_national_health_records(patient_id):
            return False
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 PHASE 2B ABDM INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        else:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Ayushman Bharat eligibility verification working")
            print("✅ Claims submission (preauth auto-approved) working")
            print("✅ Claims tracking and dashboard working")
            print("✅ National health records fetch working")
            print("✅ Consent management flow working")
        
        return failed_tests == 0

async def main():
    """Main test runner"""
    async with ABDMPhase2BTester() as tester:
        success = await tester.run_phase2b_tests()
        all_passed = tester.print_summary()
        return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)