"""
AI Lifestyle Correction Plan API
Analyzes health data from wearables, lab reports, and generates personalized
diet, workout, yoga, and lifestyle correction plans with YouTube video integration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
import os
import httpx
import asyncio
from uuid import uuid4

router = APIRouter(prefix="/ai-wellness", tags=["AI Lifestyle Correction"])

# YouTube API Configuration
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

# LLM Configuration
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


class FocusArea(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    DIABETES_CONTROL = "diabetes_control"
    CHOLESTEROL_MANAGEMENT = "cholesterol_management"
    HYPERTENSION = "hypertension"
    STRESS_MANAGEMENT = "stress_management"
    PCOS_MANAGEMENT = "pcos_management"
    THYROID_MANAGEMENT = "thyroid_management"
    BACK_PAIN = "back_pain"
    SLEEP_IMPROVEMENT = "sleep_improvement"
    GENERAL_WELLNESS = "general_wellness"
    IMMUNITY_BOOST = "immunity_boost"


class PlanDuration(str, Enum):
    TWO_WEEKS = "2_weeks"
    FOUR_WEEKS = "4_weeks"
    EIGHT_WEEKS = "8_weeks"
    TWELVE_WEEKS = "12_weeks"


class LifestylePlanRequest(BaseModel):
    patient_id: str
    focus_areas: List[FocusArea] = [FocusArea.GENERAL_WELLNESS]
    plan_duration: PlanDuration = PlanDuration.FOUR_WEEKS
    include_wearable_data: bool = True
    include_lab_reports: bool = True
    dietary_preferences: Optional[List[str]] = None  # vegetarian, vegan, etc.
    activity_level: str = "moderate"  # sedentary, light, moderate, active
    age: Optional[int] = None
    gender: Optional[str] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    health_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None


class YouTubeVideo(BaseModel):
    title: str
    channel: str
    video_id: str
    url: str
    thumbnail: str
    duration: Optional[str] = None
    language: str = "English"


class AsanaRecommendation(BaseModel):
    name: str
    sanskrit_name: str
    benefits: List[str]
    duration_minutes: int
    repetitions: Optional[int] = None
    difficulty: str  # beginner, intermediate, advanced
    contraindications: List[str] = []
    youtube_videos: List[YouTubeVideo] = []


class ExerciseRecommendation(BaseModel):
    name: str
    category: str  # cardio, strength, flexibility, balance
    duration_minutes: int
    intensity: str  # low, moderate, high
    calories_burned: Optional[int] = None
    equipment_needed: List[str] = []
    instructions: str
    youtube_videos: List[YouTubeVideo] = []


class MealPlan(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    time: str
    foods: List[str]
    calories: int
    macros: Dict[str, float]  # protein, carbs, fats in grams
    recipes: Optional[List[str]] = None


class DietPlan(BaseModel):
    daily_calorie_target: int
    macro_distribution: Dict[str, float]  # percentages
    meals: List[MealPlan]
    foods_to_include: List[str]
    foods_to_avoid: List[str]
    hydration_target_liters: float
    supplements_recommended: List[str] = []
    ayurvedic_recommendations: Optional[Dict[str, Any]] = None


class WorkoutPlan(BaseModel):
    exercises: List[ExerciseRecommendation]
    weekly_schedule: Dict[str, List[str]]  # day -> exercise names
    total_weekly_minutes: int
    rest_days: List[str]
    progression_notes: str


class YogaPlan(BaseModel):
    asanas: List[AsanaRecommendation]
    pranayama: List[Dict[str, Any]]
    meditation: List[Dict[str, Any]]
    daily_routine: Dict[str, List[str]]  # morning, evening
    total_duration_minutes: int


class LifestylePlanResponse(BaseModel):
    plan_id: str
    patient_id: str
    generated_at: str
    plan_duration: str
    focus_areas: List[str]
    health_summary: Dict[str, Any]
    diet_plan: DietPlan
    workout_plan: WorkoutPlan
    yoga_plan: YogaPlan
    weekly_schedule: Dict[str, Dict[str, Any]]
    progress_milestones: List[Dict[str, Any]]
    next_review_date: str
    recommendations: List[str]


# Curated Yoga Asanas Database
YOGA_ASANAS = {
    "surya_namaskar": {
        "name": "Sun Salutation",
        "sanskrit_name": "Surya Namaskar",
        "benefits": ["Full body stretch", "Improves circulation", "Builds strength", "Increases flexibility"],
        "duration_minutes": 15,
        "repetitions": 12,
        "difficulty": "beginner",
        "contraindications": ["Severe back pain", "Pregnancy (modify)", "High blood pressure"],
        "youtube_queries": ["surya namaskar for beginners", "sun salutation yoga tutorial"]
    },
    "bhujangasana": {
        "name": "Cobra Pose",
        "sanskrit_name": "Bhujangasana",
        "benefits": ["Strengthens spine", "Opens chest", "Improves posture", "Reduces back pain"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Pregnancy", "Carpal tunnel", "Recent abdominal surgery"],
        "youtube_queries": ["cobra pose yoga tutorial", "bhujangasana for back pain"]
    },
    "padmasana": {
        "name": "Lotus Pose",
        "sanskrit_name": "Padmasana",
        "benefits": ["Calms mind", "Improves posture", "Opens hips", "Good for meditation"],
        "duration_minutes": 10,
        "difficulty": "intermediate",
        "contraindications": ["Knee injuries", "Ankle injuries"],
        "youtube_queries": ["padmasana meditation pose", "lotus pose tutorial"]
    },
    "vrikshasana": {
        "name": "Tree Pose",
        "sanskrit_name": "Vrikshasana",
        "benefits": ["Improves balance", "Strengthens legs", "Opens hips", "Builds focus"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Severe balance issues", "Recent leg injury"],
        "youtube_queries": ["tree pose yoga beginners", "vrikshasana balance"]
    },
    "shavasana": {
        "name": "Corpse Pose",
        "sanskrit_name": "Shavasana",
        "benefits": ["Deep relaxation", "Reduces stress", "Lowers blood pressure", "Calms nervous system"],
        "duration_minutes": 10,
        "difficulty": "beginner",
        "contraindications": [],
        "youtube_queries": ["shavasana relaxation", "corpse pose guided"]
    },
    "trikonasana": {
        "name": "Triangle Pose",
        "sanskrit_name": "Trikonasana",
        "benefits": ["Stretches legs", "Opens hips", "Strengthens core", "Improves digestion"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Low blood pressure", "Neck problems"],
        "youtube_queries": ["triangle pose yoga", "trikonasana tutorial"]
    },
    "adho_mukha_svanasana": {
        "name": "Downward Dog",
        "sanskrit_name": "Adho Mukha Svanasana",
        "benefits": ["Full body stretch", "Strengthens arms", "Calms brain", "Energizes body"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Carpal tunnel", "Late pregnancy", "High blood pressure"],
        "youtube_queries": ["downward dog pose", "adho mukha svanasana"]
    },
    "setu_bandhasana": {
        "name": "Bridge Pose",
        "sanskrit_name": "Setu Bandhasana",
        "benefits": ["Strengthens back", "Opens chest", "Reduces anxiety", "Improves digestion"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Neck injury", "Knee problems"],
        "youtube_queries": ["bridge pose yoga", "setu bandhasana back pain"]
    },
    "paschimottanasana": {
        "name": "Seated Forward Bend",
        "sanskrit_name": "Paschimottanasana",
        "benefits": ["Stretches spine", "Calms mind", "Improves digestion", "Reduces anxiety"],
        "duration_minutes": 5,
        "difficulty": "beginner",
        "contraindications": ["Back injury", "Slipped disc"],
        "youtube_queries": ["seated forward bend yoga", "paschimottanasana stretch"]
    },
    "kapalbhati": {
        "name": "Skull Shining Breath",
        "sanskrit_name": "Kapalbhati Pranayama",
        "benefits": ["Cleanses respiratory system", "Improves digestion", "Energizes", "Detoxifies"],
        "duration_minutes": 10,
        "difficulty": "intermediate",
        "contraindications": ["Pregnancy", "High blood pressure", "Heart disease", "Hernia"],
        "youtube_queries": ["kapalbhati pranayama tutorial", "kapalbhati breathing"]
    },
    "anulom_vilom": {
        "name": "Alternate Nostril Breathing",
        "sanskrit_name": "Anulom Vilom",
        "benefits": ["Balances nervous system", "Reduces stress", "Improves focus", "Calms mind"],
        "duration_minutes": 10,
        "difficulty": "beginner",
        "contraindications": ["Severe cold or nasal congestion"],
        "youtube_queries": ["anulom vilom pranayama", "alternate nostril breathing"]
    },
    "vajrasana": {
        "name": "Diamond Pose",
        "sanskrit_name": "Vajrasana",
        "benefits": ["Aids digestion", "Strengthens thighs", "Good for meditation", "Reduces acidity"],
        "duration_minutes": 10,
        "difficulty": "beginner",
        "contraindications": ["Knee injury", "Ankle problems"],
        "youtube_queries": ["vajrasana after eating", "diamond pose yoga"]
    }
}

# Pranayama Database
PRANAYAMA = [
    {
        "name": "Anulom Vilom",
        "sanskrit": "अनुलोम विलोम",
        "duration_minutes": 10,
        "benefits": ["Balances energy", "Reduces anxiety", "Improves concentration"],
        "technique": "Alternate nostril breathing - inhale left, exhale right, inhale right, exhale left"
    },
    {
        "name": "Kapalbhati",
        "sanskrit": "कपालभाति",
        "duration_minutes": 10,
        "benefits": ["Detoxifies", "Improves digestion", "Energizes"],
        "technique": "Forceful exhalations with passive inhalations, 30-60 breaths per minute"
    },
    {
        "name": "Bhramari",
        "sanskrit": "भ्रामरी",
        "duration_minutes": 5,
        "benefits": ["Calms mind", "Reduces anger", "Improves sleep"],
        "technique": "Humming bee breath - close ears and make humming sound while exhaling"
    },
    {
        "name": "Ujjayi",
        "sanskrit": "उज्जायी",
        "duration_minutes": 10,
        "benefits": ["Warms body", "Calms nervous system", "Improves focus"],
        "technique": "Ocean breath - constrict throat slightly while breathing through nose"
    }
]

# Meditation Database
MEDITATION = [
    {
        "name": "Mindfulness Meditation",
        "duration_minutes": 15,
        "benefits": ["Reduces stress", "Improves awareness", "Better emotional regulation"],
        "technique": "Focus on breath, observe thoughts without judgment"
    },
    {
        "name": "Body Scan Meditation",
        "duration_minutes": 20,
        "benefits": ["Releases tension", "Improves body awareness", "Promotes relaxation"],
        "technique": "Systematically focus on each body part from toes to head"
    },
    {
        "name": "Loving-Kindness Meditation",
        "duration_minutes": 15,
        "benefits": ["Increases compassion", "Reduces negative emotions", "Improves relationships"],
        "technique": "Send wishes of love and kindness to self and others"
    }
]

# Condition-specific asana mappings
CONDITION_ASANAS = {
    FocusArea.DIABETES_CONTROL: ["surya_namaskar", "kapalbhati", "paschimottanasana", "vajrasana", "bhujangasana"],
    FocusArea.WEIGHT_LOSS: ["surya_namaskar", "trikonasana", "adho_mukha_svanasana", "kapalbhati", "setu_bandhasana"],
    FocusArea.STRESS_MANAGEMENT: ["shavasana", "anulom_vilom", "padmasana", "vrikshasana", "bhujangasana"],
    FocusArea.BACK_PAIN: ["bhujangasana", "setu_bandhasana", "trikonasana", "shavasana", "adho_mukha_svanasana"],
    FocusArea.HYPERTENSION: ["shavasana", "anulom_vilom", "vajrasana", "padmasana", "paschimottanasana"],
    FocusArea.SLEEP_IMPROVEMENT: ["shavasana", "anulom_vilom", "paschimottanasana", "vajrasana", "padmasana"],
    FocusArea.GENERAL_WELLNESS: ["surya_namaskar", "vrikshasana", "trikonasana", "bhujangasana", "shavasana"],
    FocusArea.CHOLESTEROL_MANAGEMENT: ["surya_namaskar", "kapalbhati", "setu_bandhasana", "paschimottanasana", "trikonasana"],
    FocusArea.PCOS_MANAGEMENT: ["setu_bandhasana", "bhujangasana", "kapalbhati", "paschimottanasana", "shavasana"],
    FocusArea.THYROID_MANAGEMENT: ["setu_bandhasana", "bhujangasana", "kapalbhati", "shavasana", "anulom_vilom"],
    FocusArea.IMMUNITY_BOOST: ["surya_namaskar", "kapalbhati", "anulom_vilom", "bhujangasana", "trikonasana"],
    FocusArea.WEIGHT_GAIN: ["vajrasana", "shavasana", "bhujangasana", "setu_bandhasana", "padmasana"]
}


async def fetch_youtube_videos(query: str, max_results: int = 3) -> List[YouTubeVideo]:
    """Fetch YouTube videos for a given search query"""
    
    # If no API key, return curated fallback videos
    if not YOUTUBE_API_KEY:
        return get_fallback_videos(query)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                YOUTUBE_API_URL,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "videoDuration": "medium",  # 4-20 minutes
                    "key": YOUTUBE_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return get_fallback_videos(query)
            
            data = response.json()
            videos = []
            
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                
                videos.append(YouTubeVideo(
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    video_id=video_id,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    thumbnail=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    language="English"
                ))
            
            return videos
    except Exception as e:
        print(f"YouTube API error: {e}")
        return get_fallback_videos(query)


def get_fallback_videos(query: str) -> List[YouTubeVideo]:
    """Return curated fallback videos when YouTube API is unavailable"""
    
    # Curated video database
    curated_videos = {
        "surya namaskar": [
            YouTubeVideo(
                title="Surya Namaskar for Beginners - Step by Step",
                channel="Yoga With Adriene",
                video_id="demo_surya_1",
                url="https://www.youtube.com/results?search_query=surya+namaskar+beginners",
                thumbnail="",
                language="English"
            )
        ],
        "pranayama": [
            YouTubeVideo(
                title="Pranayama Breathing Exercises for Beginners",
                channel="Yoga With Kassandra",
                video_id="demo_pranayama_1",
                url="https://www.youtube.com/results?search_query=pranayama+beginners",
                thumbnail="",
                language="English"
            )
        ],
        "meditation": [
            YouTubeVideo(
                title="10-Minute Guided Meditation for Beginners",
                channel="Headspace",
                video_id="demo_meditation_1",
                url="https://www.youtube.com/results?search_query=guided+meditation+10+minutes",
                thumbnail="",
                language="English"
            )
        ]
    }
    
    # Try to match query to curated videos
    query_lower = query.lower()
    for key, videos in curated_videos.items():
        if key in query_lower:
            return videos
    
    # Default fallback
    return [
        YouTubeVideo(
            title=f"Search: {query}",
            channel="YouTube Search",
            video_id="search",
            url=f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
            thumbnail="",
            language="English"
        )
    ]


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation"""
    if gender.lower() == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Calculate Total Daily Energy Expenditure"""
    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    return bmr * multipliers.get(activity_level, 1.55)


def generate_diet_plan(request: LifestylePlanRequest, health_data: Dict) -> DietPlan:
    """Generate personalized diet plan based on health data and goals"""
    
    # Calculate calorie needs
    weight = request.current_weight_kg or 70
    height = 170  # Default height
    age = request.age or 30
    gender = request.gender or "male"
    
    bmr = calculate_bmr(weight, height, age, gender)
    tdee = calculate_tdee(bmr, request.activity_level)
    
    # Adjust calories based on focus areas
    if FocusArea.WEIGHT_LOSS in request.focus_areas:
        daily_calories = int(tdee - 500)  # 500 calorie deficit
    elif FocusArea.WEIGHT_GAIN in request.focus_areas:
        daily_calories = int(tdee + 300)  # 300 calorie surplus
    else:
        daily_calories = int(tdee)
    
    # Macro distribution
    if FocusArea.DIABETES_CONTROL in request.focus_areas:
        macros = {"carbs": 40, "protein": 30, "fats": 30}
    elif FocusArea.WEIGHT_LOSS in request.focus_areas:
        macros = {"carbs": 35, "protein": 35, "fats": 30}
    else:
        macros = {"carbs": 50, "protein": 25, "fats": 25}
    
    # Foods to include/avoid based on conditions
    foods_include = ["Leafy greens", "Whole grains", "Lean proteins", "Nuts and seeds", "Fresh fruits"]
    foods_avoid = ["Processed foods", "Sugary drinks", "Trans fats", "Excessive salt"]
    
    if FocusArea.DIABETES_CONTROL in request.focus_areas:
        foods_include.extend(["Bitter gourd", "Fenugreek", "Cinnamon", "Low GI foods"])
        foods_avoid.extend(["White rice", "White bread", "Sugary fruits", "Fruit juices"])
    
    if FocusArea.CHOLESTEROL_MANAGEMENT in request.focus_areas:
        foods_include.extend(["Oats", "Flaxseed", "Fish (omega-3)", "Almonds"])
        foods_avoid.extend(["Red meat", "Full-fat dairy", "Fried foods", "Egg yolks"])
    
    # Generate meal plan
    meals = [
        MealPlan(
            meal_type="breakfast",
            time="7:00 AM",
            foods=["Oatmeal with nuts", "Fresh fruit", "Green tea"],
            calories=int(daily_calories * 0.25),
            macros={"protein": 15, "carbs": 45, "fats": 10}
        ),
        MealPlan(
            meal_type="mid_morning",
            time="10:00 AM",
            foods=["Mixed nuts", "Greek yogurt"],
            calories=int(daily_calories * 0.1),
            macros={"protein": 8, "carbs": 10, "fats": 8}
        ),
        MealPlan(
            meal_type="lunch",
            time="1:00 PM",
            foods=["Brown rice", "Dal/Lentils", "Vegetables", "Salad"],
            calories=int(daily_calories * 0.3),
            macros={"protein": 25, "carbs": 50, "fats": 12}
        ),
        MealPlan(
            meal_type="evening_snack",
            time="4:30 PM",
            foods=["Sprouts salad", "Herbal tea"],
            calories=int(daily_calories * 0.1),
            macros={"protein": 8, "carbs": 15, "fats": 5}
        ),
        MealPlan(
            meal_type="dinner",
            time="7:30 PM",
            foods=["Chapati", "Sabzi", "Curd", "Light soup"],
            calories=int(daily_calories * 0.25),
            macros={"protein": 20, "carbs": 35, "fats": 10}
        )
    ]
    
    # Ayurvedic recommendations
    ayurvedic = {
        "dosha_balance": "Vata-Pitta balancing recommended",
        "warm_water": "Start day with warm water and lemon",
        "spices": ["Turmeric", "Cumin", "Coriander", "Ginger"],
        "timing": "Eat largest meal at lunch when digestive fire is strongest",
        "herbs": ["Ashwagandha for stress", "Triphala for digestion", "Tulsi for immunity"]
    }
    
    return DietPlan(
        daily_calorie_target=daily_calories,
        macro_distribution=macros,
        meals=meals,
        foods_to_include=foods_include,
        foods_to_avoid=foods_avoid,
        hydration_target_liters=2.5 + (0.5 if request.activity_level in ["active", "very_active"] else 0),
        supplements_recommended=["Vitamin D3", "Omega-3", "Vitamin B12"] if age > 40 else [],
        ayurvedic_recommendations=ayurvedic
    )


def generate_workout_plan(request: LifestylePlanRequest) -> WorkoutPlan:
    """Generate personalized workout plan"""
    
    exercises = []
    
    # Cardio exercises
    if FocusArea.WEIGHT_LOSS in request.focus_areas or FocusArea.GENERAL_WELLNESS in request.focus_areas:
        exercises.append(ExerciseRecommendation(
            name="Brisk Walking",
            category="cardio",
            duration_minutes=30,
            intensity="moderate",
            calories_burned=150,
            equipment_needed=[],
            instructions="Walk at a pace where you can talk but not sing. Maintain good posture."
        ))
        exercises.append(ExerciseRecommendation(
            name="Cycling",
            category="cardio",
            duration_minutes=25,
            intensity="moderate",
            calories_burned=200,
            equipment_needed=["Bicycle or stationary bike"],
            instructions="Maintain steady pace, adjust resistance for challenge."
        ))
    
    # Strength exercises
    exercises.append(ExerciseRecommendation(
        name="Bodyweight Squats",
        category="strength",
        duration_minutes=10,
        intensity="moderate",
        calories_burned=50,
        equipment_needed=[],
        instructions="Stand feet shoulder-width apart, lower hips as if sitting, keep knees over toes."
    ))
    exercises.append(ExerciseRecommendation(
        name="Push-ups",
        category="strength",
        duration_minutes=10,
        intensity="moderate",
        calories_burned=40,
        equipment_needed=[],
        instructions="Keep body straight, lower chest to floor, push back up. Modify on knees if needed."
    ))
    
    # Flexibility
    exercises.append(ExerciseRecommendation(
        name="Stretching Routine",
        category="flexibility",
        duration_minutes=15,
        intensity="low",
        calories_burned=30,
        equipment_needed=["Yoga mat"],
        instructions="Hold each stretch for 30 seconds, breathe deeply, don't bounce."
    ))
    
    # Weekly schedule
    weekly_schedule = {
        "Monday": ["Brisk Walking", "Bodyweight Squats", "Stretching Routine"],
        "Tuesday": ["Yoga Session", "Push-ups"],
        "Wednesday": ["Cycling", "Stretching Routine"],
        "Thursday": ["Rest Day"],
        "Friday": ["Brisk Walking", "Bodyweight Squats", "Push-ups"],
        "Saturday": ["Yoga Session", "Stretching Routine"],
        "Sunday": ["Light Walking or Rest"]
    }
    
    return WorkoutPlan(
        exercises=exercises,
        weekly_schedule=weekly_schedule,
        total_weekly_minutes=180,
        rest_days=["Thursday", "Sunday"],
        progression_notes="Increase duration by 5 minutes every week. Add resistance when exercises become easy."
    )


async def generate_yoga_plan(request: LifestylePlanRequest) -> YogaPlan:
    """Generate personalized yoga plan with YouTube videos"""
    
    # Get recommended asanas based on focus areas
    recommended_asana_ids = set()
    for focus_area in request.focus_areas:
        if focus_area in CONDITION_ASANAS:
            recommended_asana_ids.update(CONDITION_ASANAS[focus_area])
    
    # If no specific focus, use general wellness
    if not recommended_asana_ids:
        recommended_asana_ids = set(CONDITION_ASANAS[FocusArea.GENERAL_WELLNESS])
    
    # Build asana recommendations with YouTube videos
    asanas = []
    for asana_id in list(recommended_asana_ids)[:6]:  # Limit to 6 asanas
        asana_data = YOGA_ASANAS.get(asana_id, {})
        if not asana_data:
            continue
        
        # Fetch YouTube videos for this asana
        videos = await fetch_youtube_videos(asana_data.get("youtube_queries", [asana_data["name"]])[0])
        
        asanas.append(AsanaRecommendation(
            name=asana_data["name"],
            sanskrit_name=asana_data["sanskrit_name"],
            benefits=asana_data["benefits"],
            duration_minutes=asana_data["duration_minutes"],
            repetitions=asana_data.get("repetitions"),
            difficulty=asana_data["difficulty"],
            contraindications=asana_data["contraindications"],
            youtube_videos=videos
        ))
    
    # Select pranayama based on conditions
    selected_pranayama = PRANAYAMA[:3]  # Select first 3
    if FocusArea.STRESS_MANAGEMENT in request.focus_areas:
        selected_pranayama = [p for p in PRANAYAMA if "calm" in str(p.get("benefits", [])).lower()][:2]
    
    # Select meditation
    selected_meditation = MEDITATION[:2]
    
    # Daily routine
    daily_routine = {
        "morning": [a.name for a in asanas[:3]] + ["Anulom Vilom", "Kapalbhati"],
        "evening": [a.name for a in asanas[3:]] + ["Shavasana", "Meditation"]
    }
    
    return YogaPlan(
        asanas=asanas,
        pranayama=selected_pranayama,
        meditation=selected_meditation,
        daily_routine=daily_routine,
        total_duration_minutes=45
    )


@router.post("/generate-plan", response_model=LifestylePlanResponse)
async def generate_lifestyle_plan(request: LifestylePlanRequest):
    """
    Generate a comprehensive AI-powered lifestyle correction plan.
    Analyzes health data and creates personalized diet, workout, and yoga plans.
    """
    
    # Fetch health data (mock for now - would integrate with wearables/lab APIs)
    health_data = {
        "avg_heart_rate": 72,
        "avg_sleep_hours": 6.5,
        "avg_steps": 5000,
        "stress_level": "moderate",
        "blood_sugar": "normal" if FocusArea.DIABETES_CONTROL not in request.focus_areas else "elevated",
        "cholesterol": "borderline" if FocusArea.CHOLESTEROL_MANAGEMENT in request.focus_areas else "normal",
        "bmi": round((request.current_weight_kg or 70) / ((170/100) ** 2), 1)
    }
    
    # Generate all components
    diet_plan = generate_diet_plan(request, health_data)
    workout_plan = generate_workout_plan(request)
    yoga_plan = await generate_yoga_plan(request)
    
    # Create weekly schedule
    weekly_schedule = {}
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        weekly_schedule[day] = {
            "morning_yoga": yoga_plan.daily_routine.get("morning", [])[:3] if day not in ["Thursday"] else ["Rest"],
            "workout": workout_plan.weekly_schedule.get(day, []),
            "evening_routine": yoga_plan.daily_routine.get("evening", [])[:2] if day not in ["Thursday", "Sunday"] else ["Relaxation"],
            "diet_focus": diet_plan.meals[0].foods[:2]  # Breakfast focus for that day
        }
    
    # Progress milestones
    milestones = [
        {"week": 1, "goal": "Establish routine, complete all scheduled sessions", "metric": "Consistency"},
        {"week": 2, "goal": "Increase water intake to target, reduce processed foods", "metric": "Nutrition"},
        {"week": 3, "goal": "Add 5 minutes to workouts, master 2 new asanas", "metric": "Fitness"},
        {"week": 4, "goal": "Review progress, adjust plan as needed", "metric": "Overall wellness"}
    ]
    
    # Calculate next review date
    duration_weeks = {"2_weeks": 2, "4_weeks": 4, "8_weeks": 8, "12_weeks": 12}
    weeks = duration_weeks.get(request.plan_duration.value, 4)
    from datetime import timedelta
    next_review = datetime.now(timezone.utc) + timedelta(weeks=weeks)
    
    # General recommendations
    recommendations = [
        "Start your day with warm water and lemon",
        "Practice yoga on an empty stomach or 3 hours after meals",
        "Stay hydrated throughout the day",
        "Get 7-8 hours of quality sleep",
        "Avoid screens 1 hour before bedtime",
        "Practice mindful eating - chew food thoroughly",
        "Take short walks after meals",
        "Practice gratitude meditation before sleep"
    ]
    
    return LifestylePlanResponse(
        plan_id=str(uuid4()),
        patient_id=request.patient_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        plan_duration=request.plan_duration.value,
        focus_areas=[f.value for f in request.focus_areas],
        health_summary=health_data,
        diet_plan=diet_plan,
        workout_plan=workout_plan,
        yoga_plan=yoga_plan,
        weekly_schedule=weekly_schedule,
        progress_milestones=milestones,
        next_review_date=next_review.isoformat(),
        recommendations=recommendations
    )


@router.get("/asanas")
async def get_available_asanas():
    """Get list of all available yoga asanas with details"""
    return {
        "total": len(YOGA_ASANAS),
        "asanas": [
            {
                "id": key,
                "name": val["name"],
                "sanskrit_name": val["sanskrit_name"],
                "difficulty": val["difficulty"],
                "benefits": val["benefits"][:2]
            }
            for key, val in YOGA_ASANAS.items()
        ]
    }


@router.get("/asana/{asana_id}/videos")
async def get_asana_videos(asana_id: str):
    """Get YouTube demonstration videos for a specific asana"""
    if asana_id not in YOGA_ASANAS:
        raise HTTPException(status_code=404, detail="Asana not found")
    
    asana = YOGA_ASANAS[asana_id]
    queries = asana.get("youtube_queries", [asana["name"]])
    
    videos = []
    for query in queries[:2]:
        query_videos = await fetch_youtube_videos(query)
        videos.extend(query_videos)
    
    return {
        "asana_id": asana_id,
        "asana_name": asana["name"],
        "videos": videos[:5]  # Max 5 videos
    }


@router.get("/focus-areas")
async def get_focus_areas():
    """Get list of available focus areas for lifestyle plans"""
    return {
        "focus_areas": [
            {"id": f.value, "name": f.value.replace("_", " ").title(), "description": get_focus_area_description(f)}
            for f in FocusArea
        ]
    }


def get_focus_area_description(focus_area: FocusArea) -> str:
    """Get description for a focus area"""
    descriptions = {
        FocusArea.WEIGHT_LOSS: "Calorie-controlled diet with cardio-focused workouts",
        FocusArea.WEIGHT_GAIN: "High-calorie nutritious diet with strength training",
        FocusArea.DIABETES_CONTROL: "Low-GI diet with blood sugar management exercises",
        FocusArea.CHOLESTEROL_MANAGEMENT: "Heart-healthy diet with cardiovascular exercises",
        FocusArea.HYPERTENSION: "Low-sodium diet with stress-reducing yoga",
        FocusArea.STRESS_MANAGEMENT: "Balanced diet with meditation and relaxation techniques",
        FocusArea.PCOS_MANAGEMENT: "Hormone-balancing diet with targeted exercises",
        FocusArea.THYROID_MANAGEMENT: "Metabolism-supporting diet with specific asanas",
        FocusArea.BACK_PAIN: "Anti-inflammatory diet with spine-strengthening exercises",
        FocusArea.SLEEP_IMPROVEMENT: "Sleep-promoting foods with evening relaxation routine",
        FocusArea.GENERAL_WELLNESS: "Balanced nutrition with holistic fitness approach",
        FocusArea.IMMUNITY_BOOST: "Nutrient-rich diet with immune-boosting practices"
    }
    return descriptions.get(focus_area, "Personalized lifestyle corrections")


@router.get("/pranayama")
async def get_pranayama_techniques():
    """Get list of pranayama breathing techniques"""
    return {"pranayama": PRANAYAMA}


@router.get("/meditation")
async def get_meditation_techniques():
    """Get list of meditation techniques"""
    return {"meditation": MEDITATION}
