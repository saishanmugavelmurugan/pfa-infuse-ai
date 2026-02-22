import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class AIMarketingService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            base_url="https://llm.emergent.sh/v1"
        )
        self.model = "gpt-4"
    
    async def analyze_campaign_performance(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enterprise-grade campaign performance analysis
        
        Args:
            campaign_data: Campaign metrics and configuration
            
        Returns:
            AI-powered insights and recommendations
        """
        try:
            prompt = f"""Analyze this marketing campaign performance data:

**Campaign Details:**
- Name: {campaign_data.get('name')}
- Platform(s): {', '.join(campaign_data.get('platforms', []))}
- Budget: ${campaign_data.get('budget', {}).get('total_budget')}
- Duration: {campaign_data.get('start_date')} to {campaign_data.get('end_date')}

**Performance Metrics:**
- Impressions: {campaign_data.get('metrics', {}).get('impressions', 0):,}
- Reach: {campaign_data.get('metrics', {}).get('reach', 0):,}
- Clicks: {campaign_data.get('metrics', {}).get('clicks', 0):,}
- Conversions: {campaign_data.get('metrics', {}).get('conversions', 0):,}
- CTR: {campaign_data.get('metrics', {}).get('click_through_rate', 0)}%
- Conversion Rate: {campaign_data.get('metrics', {}).get('conversion_rate', 0)}%
- ROI: {campaign_data.get('metrics', {}).get('roi', 0)}x
- Spent: ${campaign_data.get('budget', {}).get('spent_amount', 0)}

**Target Audience:**
{json.dumps(campaign_data.get('target_audience', {}), indent=2)}

Provide analysis in JSON format:
{{
    "overall_performance": "excellent|good|fair|poor",
    "performance_score": 0-100,
    "key_strengths": ["list of strengths"],
    "key_weaknesses": ["list of weaknesses"],
    "insights": [
        {{
            "category": "reach|engagement|conversion|budget|audience",
            "insight": "detailed insight",
            "impact": "high|medium|low",
            "data_points": ["supporting data"]
        }}
    ],
    "optimization_opportunities": [
        {{
            "area": "targeting|creative|budget|timing|platform",
            "recommendation": "specific recommendation",
            "expected_improvement": "percentage or metric",
            "priority": "high|medium|low"
        }}
    ],
    "predicted_outcomes": {{
        "if_continued": {{
            "roi": "predicted ROI",
            "conversions": "predicted conversions"
        }},
        "if_optimized": {{
            "roi": "predicted ROI with optimizations",
            "conversions": "predicted conversions"
        }}
    }},
    "next_actions": ["prioritized list of actions"]
}}"""            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert marketing analyst specializing in digital campaign optimization and data-driven decision making."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result['analysis_timestamp'] = datetime.utcnow().isoformat()
            result['ai_model'] = self.model
            
            logger.info(f"Generated campaign analysis for campaign {campaign_data.get('name')}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing campaign: {str(e)}")
            raise
    
    async def segment_customers(self, customer_data: List[Dict]) -> Dict[str, Any]:
        """AI-powered customer segmentation"""
        try:
            # Sample for AI analysis (telco-grade: don't send all data)
            sample_size = min(len(customer_data), 100)
            sample_data = customer_data[:sample_size]
            
            prompt = f"""Analyze these customer profiles and create intelligent segments:

Total Customers: {len(customer_data)}
Sample Data (first {sample_size}):
{json.dumps(sample_data, indent=2)}

Create customer segments based on:
- Demographics
- Purchase behavior
- Engagement patterns
- Lifetime value
- Churn risk

Provide segmentation in JSON format:
{{
    "segments": [
        {{
            "name": "segment name",
            "description": "detailed description",
            "size_percentage": 0-100,
            "characteristics": {{
                "demographics": {{}},
                "behaviors": {{}},
                "value_metrics": {{}}
            }},
            "value_to_business": "high|medium|low",
            "marketing_recommendations": ["list of recommendations"],
            "ideal_channels": ["list of channels"],
            "messaging_strategy": "description"
        }}
    ],
    "cross_segment_insights": ["insights across segments"],
    "opportunity_gaps": ["underserved segments or opportunities"]
}}"""            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a customer analytics expert specializing in behavioral segmentation and persona development."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error in customer segmentation: {str(e)}")
            raise
    
    async def generate_ad_copy(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered ad copy for campaigns"""
        try:
            prompt = f"""Create compelling ad copy based on this brief:

**Brand:** {brief.get('brand_name')}
**Product/Service:** {brief.get('product')}
**Target Audience:** {brief.get('target_audience')}
**Campaign Objective:** {brief.get('objective')}
**Tone:** {brief.get('tone', 'professional')}
**Platform:** {brief.get('platform')}
**Key Message:** {brief.get('key_message')}
**Call-to-Action:** {brief.get('cta')}

Generate multiple variations in JSON format:
{{
    "variations": [
        {{
            "headline": "attention-grabbing headline (max 60 chars)",
            "body_text": "compelling body copy (max 150 chars)",
            "cta": "call to action",
            "tone": "description of tone used",
            "target_emotion": "emotion being targeted",
            "predicted_performance": "high|medium|low",
            "reasoning": "why this copy should work"
        }}
    ],
    "best_practices": ["list of copywriting best practices applied"],
    "a_b_test_recommendations": ["what elements to test"]
}}"""            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior copywriter specializing in conversion-focused advertising across digital platforms."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher for creativity
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error generating ad copy: {str(e)}")
            raise
    
    async def pre_launch_analysis(self, campaign_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Telco-grade pre-launch feasibility analysis"""
        try:
            prompt = f"""Conduct a comprehensive pre-launch analysis for this campaign:

**Campaign Details:**
{json.dumps(campaign_plan, indent=2)}

**Market Context:**
- Industry: {campaign_plan.get('industry')}
- Competition Level: {campaign_plan.get('competition_level', 'unknown')}
- Budget: ${campaign_plan.get('budget')}
- Target Market Size: {campaign_plan.get('target_market_size', 'unknown')}

Provide feasibility analysis in JSON format:
{{
    "feasibility_score": 0-100,
    "recommendation": "go|optimize_first|no_go",
    "market_analysis": {{
        "market_size": "estimated size",
        "market_saturation": "low|medium|high",
        "competition_intensity": "low|medium|high",
        "market_trends": ["relevant trends"]
    }},
    "risk_assessment": [
        {{
            "risk": "description",
            "severity": "low|medium|high|critical",
            "probability": "low|medium|high",
            "mitigation": "how to mitigate"
        }}
    ],
    "opportunity_assessment": [
        {{
            "opportunity": "description",
            "potential_impact": "description",
            "actionability": "easy|moderate|difficult"
        }}
    ],
    "budget_analysis": {{
        "adequacy": "sufficient|tight|insufficient",
        "recommended_allocation": {{}},
        "expected_burn_rate": "description"
    }},
    "audience_validation": {{
        "target_audience_clarity": "clear|unclear",
        "audience_reachability": "easy|moderate|difficult",
        "audience_size": "estimated size"
    }},
    "predicted_outcomes": {{
        "best_case": {{}},
        "expected_case": {{}},
        "worst_case": {{}}
    }},
    "launch_readiness_checklist": [
        {{
            "item": "checklist item",
            "status": "ready|needs_work|missing",
            "priority": "critical|high|medium|low"
        }}
    ],
    "final_recommendation": "detailed recommendation with reasoning"
}}"""            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strategic marketing consultant with expertise in campaign planning, market analysis, and ROI prediction."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower for analytical consistency
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result['analysis_date'] = datetime.utcnow().isoformat()
            
            logger.info("Generated pre-launch analysis")
            return result
            
        except Exception as e:
            logger.error(f"Error in pre-launch analysis: {str(e)}")
            raise
    
    async def optimize_ad_creative(self, ad_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered ad creative optimization"""
        try:
            prompt = f"""Analyze and optimize this ad creative:

**Ad Details:**
{json.dumps(ad_data, indent=2)}

**Test Results:**
- Test Audience Size: {ad_data.get('test_audience_size')}
- Impressions: {ad_data.get('test_metrics', {}).get('impressions', 0)}
- CTR: {ad_data.get('test_metrics', {}).get('ctr', 0)}%
- Engagement Rate: {ad_data.get('test_metrics', {}).get('engagement_rate', 0)}%

Provide optimization recommendations in JSON format:
{{
    "performance_score": 0-100,
    "overall_assessment": "description",
    "strengths": ["what's working well"],
    "weaknesses": ["what needs improvement"],
    "optimization_recommendations": [
        {{
            "element": "headline|image|cta|copy|targeting",
            "current": "current state",
            "recommended": "recommended change",
            "expected_impact": "percentage improvement",
            "priority": "high|medium|low"
        }}
    ],
    "a_b_test_suggestions": [
        {{
            "test_element": "what to test",
            "variation_a": "current version",
            "variation_b": "suggested alternative",
            "hypothesis": "what you expect to learn"
        }}
    ],
    "best_practices_violations": ["practices not being followed"],
    "predicted_performance_if_optimized": {{
        "ctr_improvement": "percentage",
        "engagement_improvement": "percentage",
        "roi_impact": "description"
    }}
}}"""            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative optimization specialist with deep expertise in ad performance, psychology, and conversion optimization."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing ad creative: {str(e)}")
            raise

# Singleton instance
ai_marketing_service = AIMarketingService()
