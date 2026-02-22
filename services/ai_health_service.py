import os
import json
import logging
from typing import Dict, List, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIHealthService:
    def __init__(self):
        # Use Emergent LLM key for AI predictions
        self.client = AsyncOpenAI(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            base_url="https://llm.emergent.sh/v1"
        )
        self.model = "gpt-4"
    
    async def predict_health_risks(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Enterprise-grade health risk prediction using AI
        
        Args:
            user_data: Dictionary containing user's health information
            
        Returns:
            List of health risk predictions with confidence scores
        """
        try:
            # Build comprehensive prompt
            prompt = self._build_health_analysis_prompt(user_data)
            
            # Call AI model
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an advanced medical AI assistant specialized in preventive healthcare and risk prediction.
                        Analyze patient data and predict potential health risks 6-18 months in advance.
                        Provide evidence-based recommendations combining modern medicine and Ayurvedic practices.
                        Return predictions in structured JSON format."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent medical predictions
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse AI response
            result = json.loads(response.choices[0].message.content)
            predictions = result.get('predictions', [])
            
            # Add confidence scores and metadata
            for prediction in predictions:
                prediction['ai_model_version'] = self.model
                prediction['ai_confidence'] = prediction.get('confidence', 90.0)
            
            logger.info(f"Generated {len(predictions)} health risk predictions for user")
            return predictions
            
        except Exception as e:
            logger.error(f"Error in health risk prediction: {str(e)}")
            raise Exception(f"Failed to generate health predictions: {str(e)}")
    
    def _build_health_analysis_prompt(self, user_data: Dict[str, Any]) -> str:
        """Build detailed prompt for health analysis"""
        
        prompt = f"""Analyze the following patient data and predict potential health risks:

**Patient Information:**
- Age: {user_data.get('age', 'N/A')}
- Gender: {user_data.get('gender', 'N/A')}
- Current Health Score: {user_data.get('health_score', 'N/A')}/100

**Vital Signs:**
{json.dumps(user_data.get('vital_signs', {}), indent=2)}

**Medical History:**
{json.dumps(user_data.get('medical_history', []), indent=2)}

**Lifestyle Factors:**
{json.dumps(user_data.get('lifestyle', {}), indent=2)}

**Current Medications:**
{json.dumps(user_data.get('medications', []), indent=2)}

**Family History:**
{json.dumps(user_data.get('family_history', []), indent=2)}

Please analyze this data and provide health risk predictions in JSON format with predictions array containing risk_category, risk_level, probability, timeframe, confidence, key_indicators, recommendations, diagnostic_tests, and reasoning fields.

Focus on preventive care and provide actionable recommendations."""
        
        return prompt
    
    async def generate_ayurvedic_recommendations(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized Ayurvedic recommendations"""
        try:
            prompt = f"""Based on the following patient information, provide personalized Ayurvedic recommendations:

Age: {user_data.get('age')}
Gender: {user_data.get('gender')}
Current Health Issues: {user_data.get('health_issues', [])}
Symptoms: {user_data.get('symptoms', [])}

Provide recommendations in JSON format with dosha_assessment and recommendations fields."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an Ayurvedic medicine expert. Provide authentic, safe, and effective recommendations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error generating Ayurvedic recommendations: {str(e)}")
            raise
    
    async def analyze_medication_interactions(self, medications: List[Dict]) -> Dict[str, Any]:
        """Analyze potential medication interactions"""
        try:
            meds_list = [f"{m.get('name')} ({m.get('dosage')})" for m in medications]
            
            prompt = f"""Analyze potential interactions between these medications:
{json.dumps(meds_list, indent=2)}

Provide analysis in JSON format with has_interactions, severity, interactions array, and safe_alternatives fields."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a clinical pharmacologist. Analyze medication interactions with precision."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Very low temperature for medical safety
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing medication interactions: {str(e)}")
            raise

# Singleton instance
ai_health_service = AIHealthService()
