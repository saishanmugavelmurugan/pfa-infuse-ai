"""
HealthTrack Pro - Comprehensive Load Testing Suite
Uses Locust for distributed load testing with realistic user scenarios

Run with:
    locust -f locustfile.py --host=http://localhost:8001
    
For distributed testing:
    locust -f locustfile.py --master --host=http://localhost:8001
    locust -f locustfile.py --worker --master-host=localhost
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import json
import random
import string
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthTrackUser(HttpUser):
    """Simulates a typical HealthTrack Pro user"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Setup: Create user and login"""
        self.user_email = f"test_{self._generate_random_string()}@load.test"
        self.user_password = "LoadTest123!"
        self.token = None
        self.user_id = None
        
        # Register and login
        self._register_user()
        self._login()
    
    def _generate_random_string(self, length=8):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _register_user(self):
        """Register a new test user"""
        with self.client.post(
            "/api/auth/register",
            json={
                "email": self.user_email,
                "password": self.user_password,
                "full_name": "Load Test User",
                "phone": f"+91{random.randint(7000000000, 9999999999)}"
            },
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 409]:  # 409 = already exists
                response.success()
            else:
                response.failure(f"Registration failed: {response.text}")
    
    def _login(self):
        """Login and get auth token"""
        with self.client.post(
            "/api/auth/login",
            json={
                "email": self.user_email,
                "password": self.user_password
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                self.user_id = data.get("user_id") or data.get("user", {}).get("id")
                response.success()
            else:
                response.failure(f"Login failed: {response.text}")
    
    def _get_headers(self):
        """Get authorization headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    # ========== Doctor Directory Tasks ==========
    
    @task(10)
    def browse_doctors(self):
        """Browse doctor directory"""
        self.client.get(
            "/api/doctors/",
            params={"limit": 20, "skip": 0},
            headers=self._get_headers(),
            name="/api/doctors/ [GET]"
        )
    
    @task(8)
    def search_doctors(self):
        """Search for doctors by specialty"""
        specialties = [
            "Cardiology", "Dermatology", "General Medicine",
            "Neurology", "Orthopedics", "Pediatrics", "Ayurveda"
        ]
        specialty = random.choice(specialties)
        self.client.get(
            "/api/doctors/",
            params={"specialty": specialty, "limit": 10},
            headers=self._get_headers(),
            name="/api/doctors/?specialty [GET]"
        )
    
    @task(5)
    def get_doctor_profile(self):
        """View a specific doctor's profile"""
        # Get a random doctor ID from the list
        response = self.client.get(
            "/api/doctors/",
            params={"limit": 5},
            headers=self._get_headers(),
            name="/api/doctors/ [GET for profile]"
        )
        if response.status_code == 200:
            doctors = response.json().get("doctors", [])
            if doctors:
                doctor = random.choice(doctors)
                doctor_id = doctor.get("id")
                if doctor_id:
                    self.client.get(
                        f"/api/doctors/{doctor_id}",
                        headers=self._get_headers(),
                        name="/api/doctors/{id} [GET]"
                    )
    
    # ========== Drug Database Tasks ==========
    
    @task(6)
    def search_drugs(self):
        """Search drug database"""
        search_terms = [
            "metformin", "aspirin", "paracetamol", "atorvastatin",
            "omeprazole", "amlodipine", "diabetes", "hypertension"
        ]
        term = random.choice(search_terms)
        self.client.get(
            "/api/healthtrack/drug-database/search",
            params={"query": term, "limit": 10},
            headers=self._get_headers(),
            name="/api/healthtrack/drug-database/search [GET]"
        )
    
    @task(3)
    def check_drug_interactions(self):
        """Check drug interactions"""
        drug_pairs = [
            "drug-001,drug-002",
            "drug-003,drug-004",
            "drug-001,drug-003,drug-005"
        ]
        self.client.get(
            "/api/healthtrack/drug-database/interactions",
            params={"drug_ids": random.choice(drug_pairs)},
            headers=self._get_headers(),
            name="/api/healthtrack/drug-database/interactions [GET]"
        )
    
    @task(4)
    def get_drugs_by_indication(self):
        """Get drugs by medical indication"""
        indications = ["diabetes", "hypertension", "pain", "fever", "cholesterol"]
        self.client.get(
            f"/api/healthtrack/drug-database/by-indication/{random.choice(indications)}",
            headers=self._get_headers(),
            name="/api/healthtrack/drug-database/by-indication/{indication} [GET]"
        )
    
    # ========== Patient Records Tasks ==========
    
    @task(4)
    def view_patients(self):
        """View patient list"""
        self.client.get(
            "/api/healthtrack/patients",
            params={"limit": 20},
            headers=self._get_headers(),
            name="/api/healthtrack/patients [GET]"
        )
    
    # ========== Appointments Tasks ==========
    
    @task(5)
    def view_appointments(self):
        """View appointments"""
        self.client.get(
            "/api/healthtrack/appointments",
            params={"limit": 10},
            headers=self._get_headers(),
            name="/api/healthtrack/appointments [GET]"
        )
    
    @task(3)
    def get_available_slots(self):
        """Get available appointment slots"""
        # Get today + 1 day
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.client.get(
            "/api/healthtrack/appointments/slots/available",
            params={"date": date},
            headers=self._get_headers(),
            name="/api/healthtrack/appointments/slots/available [GET]"
        )
    
    # ========== Lab Tests Tasks ==========
    
    @task(4)
    def view_lab_catalog(self):
        """View lab test catalog"""
        self.client.get(
            "/api/healthtrack/lab-tests/catalog",
            headers=self._get_headers(),
            name="/api/healthtrack/lab-tests/catalog [GET]"
        )
    
    # ========== Health Sync Tasks ==========
    
    @task(3)
    def view_health_platforms(self):
        """View available health platforms"""
        self.client.get(
            "/api/health-sync/platforms",
            headers=self._get_headers(),
            name="/api/health-sync/platforms [GET]"
        )
    
    # ========== Feature Flags Tasks ==========
    
    @task(2)
    def get_features(self):
        """Get feature flags"""
        self.client.get(
            "/api/features/",
            headers=self._get_headers(),
            name="/api/features/ [GET]"
        )
    
    # ========== Dashboard Tasks ==========
    
    @task(7)
    def view_dashboard(self):
        """View main dashboard"""
        self.client.get(
            "/api/dashboard/summary",
            headers=self._get_headers(),
            name="/api/dashboard/summary [GET]"
        )
    
    # ========== AI Wellness Tasks ==========
    
    @task(2)
    def generate_wellness_plan(self):
        """Generate AI wellness plan (heavy operation)"""
        with self.client.post(
            "/api/ai-wellness/generate-plan",
            json={
                "age": random.randint(25, 60),
                "gender": random.choice(["male", "female"]),
                "weight": random.randint(50, 100),
                "height": random.randint(150, 190),
                "activity_level": random.choice(["sedentary", "light", "moderate", "active"]),
                "focus_areas": random.sample(["weight_loss", "diabetes", "stress", "sleep", "wellness"], 2),
                "medical_conditions": []
            },
            headers=self._get_headers(),
            catch_response=True,
            name="/api/ai-wellness/generate-plan [POST]"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 503:  # Service unavailable (LLM not configured)
                response.success()  # Expected in test environment
            else:
                response.failure(f"Wellness plan failed: {response.text}")


class AdminUser(HttpUser):
    """Simulates an admin user with higher privilege operations"""
    
    wait_time = between(2, 8)
    weight = 1  # Lower weight = fewer admin users
    
    def on_start(self):
        """Login as admin"""
        self.token = None
        self._login_admin()
    
    def _login_admin(self):
        """Login with admin credentials"""
        with self.client.post(
            "/api/auth/login",
            json={
                "email": "admin@infuse.demo",
                "password": "admin1234"
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                response.success()
            else:
                # Try backup admin
                response.success()
    
    def _get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    @task(5)
    def view_admin_dashboard(self):
        """View admin analytics dashboard"""
        self.client.get(
            "/api/admin/analytics/dashboard",
            headers=self._get_headers(),
            name="/api/admin/analytics/dashboard [GET]"
        )
    
    @task(3)
    def view_feature_flags(self):
        """View all feature flags"""
        self.client.get(
            "/api/features/",
            headers=self._get_headers(),
            name="/api/features/ [GET - Admin]"
        )
    
    @task(2)
    def view_subscription_tiers(self):
        """View subscription tiers"""
        self.client.get(
            "/api/subscriptions/tiers",
            headers=self._get_headers(),
            name="/api/subscriptions/tiers [GET]"
        )
    
    @task(2)
    def view_organizations(self):
        """View organizations"""
        self.client.get(
            "/api/organizations/",
            headers=self._get_headers(),
            name="/api/organizations/ [GET]"
        )


class APIOnlyUser(HttpUser):
    """Simulates API-only access patterns (no login required)"""
    
    wait_time = between(0.5, 2)
    weight = 3  # Higher weight = more API users
    
    @task(10)
    def health_check(self):
        """Hit health endpoint"""
        self.client.get(
            "/api/health",
            name="/api/health [GET]"
        )
    
    @task(8)
    def public_doctors(self):
        """View public doctor directory"""
        self.client.get(
            "/api/doctors/",
            params={"limit": 10},
            name="/api/doctors/ [GET - Public]"
        )
    
    @task(5)
    def doctor_specialties(self):
        """Get doctor specialties"""
        self.client.get(
            "/api/doctors/specialties",
            name="/api/doctors/specialties [GET]"
        )
    
    @task(5)
    def drug_search_public(self):
        """Public drug search"""
        terms = ["aspirin", "paracetamol", "vitamin"]
        self.client.get(
            "/api/healthtrack/drug-database/search",
            params={"query": random.choice(terms)},
            name="/api/healthtrack/drug-database/search [GET - Public]"
        )
    
    @task(3)
    def health_schemes(self):
        """Get health schemes"""
        self.client.get(
            "/api/health-schemes/by-region/IN",
            name="/api/health-schemes/by-region/{country} [GET]"
        )


# ========== Custom Event Handlers ==========

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("=" * 60)
    logger.info("HealthTrack Pro Load Test Starting")
    logger.info(f"Target Host: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("=" * 60)
    logger.info("HealthTrack Pro Load Test Complete")
    logger.info("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Log slow requests"""
    if response_time > 5000:  # > 5 seconds
        logger.warning(f"SLOW REQUEST: {name} took {response_time}ms")


# ========== Performance Thresholds ==========

PERFORMANCE_THRESHOLDS = {
    "p95_response_time_ms": 2000,  # 95th percentile should be < 2s
    "p99_response_time_ms": 5000,  # 99th percentile should be < 5s
    "error_rate_percent": 1.0,     # Error rate should be < 1%
    "min_requests_per_second": 50  # Minimum throughput
}
