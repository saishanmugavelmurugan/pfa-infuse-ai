"""
Prakriti (Dosha) ML Classifier
Classifies user's Ayurvedic constitution: Vata, Pitta, Kapha
Based on questionnaire responses + biometric data
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score
from typing import Dict, List, Tuple, Optional
import json
import os
import pickle

class PrakritiClassifier:
    """
    ML-based Prakriti (Ayurvedic Constitution) Classifier
    Uses Random Forest + Gradient Boosting ensemble
    Accuracy target: 85%+ based on research
    """
    
    DOSHAS = ['Vata', 'Pitta', 'Kapha', 'Vata-Pitta', 'Pitta-Kapha', 'Vata-Kapha', 'Tridosha']
    
    # Feature definitions based on Ayurvedic assessment
    QUESTIONNAIRE_FEATURES = [
        'body_frame',        # 1=thin/light, 2=medium, 3=large/heavy
        'weight_tendency',   # 1=hard to gain, 2=moderate, 3=easy to gain
        'skin_type',         # 1=dry/rough, 2=warm/oily, 3=thick/moist
        'hair_type',         # 1=dry/frizzy, 2=fine/early gray, 3=thick/oily
        'appetite',          # 1=irregular, 2=strong/irritable, 3=steady/slow
        'digestion',         # 1=irregular/gas, 2=fast/acidic, 3=slow/heavy
        'sleep_pattern',     # 1=light/interrupted, 2=moderate, 3=deep/long
        'stress_response',   # 1=anxiety/worry, 2=anger/irritation, 3=withdrawal/depression
        'climate_preference',# 1=warm, 2=cool, 3=warm/dry
        'activity_level',    # 1=very active/restless, 2=moderate/focused, 3=slow/steady
        'speech_pattern',    # 1=fast/talkative, 2=sharp/precise, 3=slow/melodious
        'memory',            # 1=quick to learn/forget, 2=sharp/clear, 3=slow to learn/remember
        'creativity',        # 1=highly creative, 2=practical/logical, 3=methodical/caring
        'emotional_nature',  # 1=fearful/anxious, 2=intense/passionate, 3=calm/attached
        'physical_endurance' # 1=low/variable, 2=moderate/determined, 3=high/steady
    ]
    
    BIOMETRIC_FEATURES = [
        'bmi',
        'resting_heart_rate',
        'blood_pressure_systolic',
        'blood_pressure_diastolic',
        'body_temperature',
        'sleep_hours_avg',
        'activity_level_score'
    ]
    
    def __init__(self):
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self._initialize_with_synthetic_data()
    
    def _generate_synthetic_training_data(self, n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data based on Ayurvedic characteristics"""
        np.random.seed(42)
        X = []
        y = []
        
        # Dosha characteristic profiles
        profiles = {
            'Vata': {
                'questionnaire': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                'biometrics': [18, 75, 110, 70, 36.2, 6, 8]
            },
            'Pitta': {
                'questionnaire': [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                'biometrics': [23, 72, 125, 80, 36.8, 7, 7]
            },
            'Kapha': {
                'questionnaire': [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
                'biometrics': [28, 65, 120, 75, 36.4, 8, 5]
            },
            'Vata-Pitta': {
                'questionnaire': [1.5, 1.5, 1.5, 1.5, 1.5, 2, 1, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5],
                'biometrics': [20, 74, 118, 75, 36.5, 6.5, 7.5]
            },
            'Pitta-Kapha': {
                'questionnaire': [2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5],
                'biometrics': [26, 68, 122, 78, 36.6, 7.5, 6]
            },
            'Vata-Kapha': {
                'questionnaire': [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                'biometrics': [24, 70, 115, 72, 36.3, 7, 6.5]
            },
            'Tridosha': {
                'questionnaire': [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                'biometrics': [22, 70, 120, 75, 36.5, 7, 6.5]
            }
        }
        
        samples_per_dosha = n_samples // len(profiles)
        
        for dosha, profile in profiles.items():
            for _ in range(samples_per_dosha):
                # Add noise to questionnaire responses
                q_features = [max(1, min(3, v + np.random.normal(0, 0.3))) for v in profile['questionnaire']]
                # Add noise to biometrics
                b_features = [v + np.random.normal(0, v * 0.1) for v in profile['biometrics']]
                
                X.append(q_features + b_features)
                y.append(dosha)
        
        return np.array(X), np.array(y)
    
    def _initialize_with_synthetic_data(self):
        """Initialize model with synthetic data"""
        X, y = self._generate_synthetic_training_data(2000)
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        self.rf_model.fit(X_scaled, y_encoded)
        self.gb_model.fit(X_scaled, y_encoded)
        
        self.is_trained = True
    
    def predict_prakriti(self, questionnaire_responses: Dict[str, int], 
                         biometrics: Optional[Dict[str, float]] = None) -> Dict:
        """
        Predict Prakriti based on questionnaire and optional biometrics
        
        Args:
            questionnaire_responses: Dict with keys matching QUESTIONNAIRE_FEATURES
            biometrics: Optional dict with keys matching BIOMETRIC_FEATURES
        
        Returns:
            Dict with prakriti prediction, confidence, and dosha breakdown
        """
        # Build feature vector
        q_features = [questionnaire_responses.get(f, 2) for f in self.QUESTIONNAIRE_FEATURES]
        
        if biometrics:
            b_features = [
                biometrics.get('bmi', 22),
                biometrics.get('resting_heart_rate', 70),
                biometrics.get('blood_pressure_systolic', 120),
                biometrics.get('blood_pressure_diastolic', 75),
                biometrics.get('body_temperature', 36.5),
                biometrics.get('sleep_hours_avg', 7),
                biometrics.get('activity_level_score', 6)
            ]
        else:
            b_features = [22, 70, 120, 75, 36.5, 7, 6]
        
        features = np.array(q_features + b_features).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        
        # Get predictions from both models
        rf_proba = self.rf_model.predict_proba(features_scaled)[0]
        gb_proba = self.gb_model.predict_proba(features_scaled)[0]
        
        # Ensemble averaging
        ensemble_proba = (rf_proba + gb_proba) / 2
        
        predicted_idx = np.argmax(ensemble_proba)
        predicted_dosha = self.label_encoder.inverse_transform([predicted_idx])[0]
        confidence = float(ensemble_proba[predicted_idx])
        
        # Calculate individual dosha percentages
        dosha_breakdown = self._calculate_dosha_breakdown(questionnaire_responses)
        
        return {
            'prakriti': predicted_dosha,
            'confidence': round(confidence * 100, 1),
            'dosha_breakdown': dosha_breakdown,
            'dominant_dosha': self._get_dominant_dosha(dosha_breakdown),
            'secondary_dosha': self._get_secondary_dosha(dosha_breakdown),
            'all_probabilities': {
                self.label_encoder.inverse_transform([i])[0]: round(float(p) * 100, 1)
                for i, p in enumerate(ensemble_proba)
            }
        }
    
    def _calculate_dosha_breakdown(self, responses: Dict[str, int]) -> Dict[str, float]:
        """Calculate percentage breakdown of each dosha"""
        vata_score = 0
        pitta_score = 0
        kapha_score = 0
        
        for feature, value in responses.items():
            if value <= 1.5:
                vata_score += 1
            elif value <= 2.5:
                pitta_score += 1
            else:
                kapha_score += 1
        
        total = vata_score + pitta_score + kapha_score
        if total == 0:
            return {'Vata': 33.3, 'Pitta': 33.3, 'Kapha': 33.4}
        
        return {
            'Vata': round(vata_score / total * 100, 1),
            'Pitta': round(pitta_score / total * 100, 1),
            'Kapha': round(kapha_score / total * 100, 1)
        }
    
    def _get_dominant_dosha(self, breakdown: Dict[str, float]) -> str:
        return max(breakdown, key=breakdown.get)
    
    def _get_secondary_dosha(self, breakdown: Dict[str, float]) -> str:
        sorted_doshas = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        return sorted_doshas[1][0] if len(sorted_doshas) > 1 else sorted_doshas[0][0]
    
    def get_recommendations(self, prakriti: str) -> Dict:
        """Get personalized recommendations based on Prakriti"""
        recommendations = {
            'Vata': {
                'diet': [
                    'Warm, cooked, moist foods',
                    'Sweet, sour, salty tastes',
                    'Regular meal times',
                    'Avoid cold, dry, raw foods'
                ],
                'lifestyle': [
                    'Regular daily routine',
                    'Warm oil massage (Abhyanga)',
                    'Gentle yoga and meditation',
                    'Early to bed, adequate sleep'
                ],
                'herbs': [
                    'Ashwagandha for stress',
                    'Triphala for digestion',
                    'Brahmi for mind calming',
                    'Ginger tea for warmth'
                ],
                'yoga': ['Slow Sun Salutations', 'Forward bends', 'Savasana', 'Pranayama - Nadi Shodhana'],
                'avoid': ['Excessive travel', 'Cold weather exposure', 'Irregular schedules', 'Stimulants']
            },
            'Pitta': {
                'diet': [
                    'Cool, refreshing foods',
                    'Sweet, bitter, astringent tastes',
                    'Avoid spicy, oily, fried foods',
                    'Plenty of water and coconut water'
                ],
                'lifestyle': [
                    'Cooling activities',
                    'Moonlight walks',
                    'Swimming',
                    'Moderate exercise, avoid overheating'
                ],
                'herbs': [
                    'Amalaki for cooling',
                    'Neem for skin health',
                    'Shatavari for hormonal balance',
                    'Mint tea for cooling'
                ],
                'yoga': ['Moon Salutations', 'Cooling pranayama (Sheetali)', 'Twists', 'Forward folds'],
                'avoid': ['Hot spicy foods', 'Excessive sun', 'Overworking', 'Alcohol']
            },
            'Kapha': {
                'diet': [
                    'Light, warm, dry foods',
                    'Pungent, bitter, astringent tastes',
                    'Avoid heavy, oily, cold foods',
                    'Light breakfast or skip'
                ],
                'lifestyle': [
                    'Vigorous daily exercise',
                    'Dry brushing before shower',
                    'Early rising',
                    'Varied routine to avoid stagnation'
                ],
                'herbs': [
                    'Trikatu for metabolism',
                    'Guggulu for weight management',
                    'Punarnava for fluid balance',
                    'Ginger-honey tea'
                ],
                'yoga': ['Vigorous Sun Salutations', 'Backbends', 'Kapalabhati pranayama', 'Standing poses'],
                'avoid': ['Daytime sleeping', 'Excessive sweets', 'Cold/damp environments', 'Sedentary lifestyle']
            }
        }
        
        # Handle dual doshas
        if '-' in prakriti:
            doshas = prakriti.split('-')
            combined = {'diet': [], 'lifestyle': [], 'herbs': [], 'yoga': [], 'avoid': []}
            for dosha in doshas:
                if dosha in recommendations:
                    for key in combined:
                        combined[key].extend(recommendations[dosha][key][:2])
            return combined
        
        return recommendations.get(prakriti, recommendations['Vata'])


# Singleton instance
_prakriti_classifier = None

def get_prakriti_classifier() -> PrakritiClassifier:
    global _prakriti_classifier
    if _prakriti_classifier is None:
        _prakriti_classifier = PrakritiClassifier()
    return _prakriti_classifier
