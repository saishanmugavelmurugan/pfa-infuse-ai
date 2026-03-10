"""
Ayurveda RAG (Retrieval-Augmented Generation) System
Retrieves relevant Ayurvedic knowledge for personalized recommendations
"""

from typing import Dict, List, Optional, Tuple
import json
import re

class AyurvedaKnowledgeBase:
    """
    Knowledge base of Ayurvedic texts and remedies
    Used for RAG-based recommendation generation
    """
    
    def __init__(self):
        self.remedies_db = self._load_remedies()
        self.herbs_db = self._load_herbs()
        self.yoga_db = self._load_yoga()
        self.diet_db = self._load_diet()
    
    def _load_remedies(self) -> Dict:
        """Classical Ayurvedic remedies by condition"""
        return {
            'stress': {
                'vata': {
                    'herbs': ['Ashwagandha', 'Jatamansi', 'Brahmi'],
                    'treatments': ['Shirodhara', 'Abhyanga with warm sesame oil'],
                    'diet': ['Warm milk with nutmeg', 'Ghee in food', 'Regular meals'],
                    'lifestyle': ['Regular routine', 'Early bedtime', 'Gentle yoga'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana'
                },
                'pitta': {
                    'herbs': ['Brahmi', 'Shankhapushpi', 'Amalaki'],
                    'treatments': ['Shirodhara with coconut oil', 'Cool compresses'],
                    'diet': ['Cooling foods', 'Sweet fruits', 'Coconut water'],
                    'lifestyle': ['Moonlight walks', 'Swimming', 'Avoid midday sun'],
                    'classical_reference': 'Ashtanga Hridaya, Sutrasthana'
                },
                'kapha': {
                    'herbs': ['Brahmi', 'Vacha', 'Trikatu'],
                    'treatments': ['Dry massage', 'Vigorous exercise'],
                    'diet': ['Light foods', 'Spices', 'Honey'],
                    'lifestyle': ['Active morning routine', 'Varied activities'],
                    'classical_reference': 'Sushruta Samhita, Sutrasthana'
                }
            },
            'digestion': {
                'vata': {
                    'herbs': ['Triphala', 'Hingvastak', 'Ginger'],
                    'treatments': ['Warm water intake', 'Abdominal massage'],
                    'diet': ['Warm, cooked foods', 'Small frequent meals', 'Ginger before meals'],
                    'lifestyle': ['Eat in calm environment', 'Regular meal times'],
                    'classical_reference': 'Charaka Samhita, Vimana Sthana'
                },
                'pitta': {
                    'herbs': ['Amalaki', 'Licorice', 'Coriander'],
                    'treatments': ['Aloe vera juice', 'Cooling herbs'],
                    'diet': ['Cooling foods', 'Avoid spicy/acidic', 'Fennel seeds'],
                    'lifestyle': ['Eat at regular times', 'Avoid eating when angry'],
                    'classical_reference': 'Ashtanga Hridaya, Nidana Sthana'
                },
                'kapha': {
                    'herbs': ['Trikatu', 'Chitrak', 'Ginger'],
                    'treatments': ['Fasting', 'Hot water', 'Digestive spices'],
                    'diet': ['Light foods', 'Avoid heavy/oily', 'Warm spiced drinks'],
                    'lifestyle': ['Exercise before meals', 'Small portions'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana'
                }
            },
            'sleep': {
                'vata': {
                    'herbs': ['Ashwagandha', 'Jatamansi', 'Tagara'],
                    'treatments': ['Warm oil foot massage', 'Head massage'],
                    'diet': ['Warm milk with nutmeg', 'Light dinner', 'Avoid caffeine'],
                    'lifestyle': ['Consistent bedtime', 'Warm bath', 'Calm evening routine'],
                    'classical_reference': 'Charaka Samhita, Sutrasthana'
                },
                'pitta': {
                    'herbs': ['Brahmi', 'Shankhapushpi', 'Rose'],
                    'treatments': ['Cool room temperature', 'Coconut oil massage'],
                    'diet': ['Avoid late heavy meals', 'Cooling milk', 'No alcohol'],
                    'lifestyle': ['No screens before bed', 'Cool bedroom'],
                    'classical_reference': 'Ashtanga Hridaya, Sutrasthana'
                },
                'kapha': {
                    'herbs': ['Vacha', 'Trikatu', 'Tulsi'],
                    'treatments': ['Dry brush massage', 'Earlier dinner'],
                    'diet': ['Light dinner', 'Avoid sweets at night', 'Ginger tea'],
                    'lifestyle': ['No daytime sleeping', 'Active evening', 'Early wake time'],
                    'classical_reference': 'Sushruta Samhita, Sutrasthana'
                }
            },
            'immunity': {
                'general': {
                    'herbs': ['Chyawanprash', 'Guduchi', 'Amalaki', 'Tulsi'],
                    'treatments': ['Rasayana therapy', 'Panchakarma seasonal cleanse'],
                    'diet': ['Fresh seasonal foods', 'Six tastes daily', 'Avoid processed foods'],
                    'lifestyle': ['Daily routine (Dinacharya)', 'Seasonal routine (Ritucharya)'],
                    'classical_reference': 'Charaka Samhita, Rasayana Adhyaya'
                }
            },
            'joint_pain': {
                'vata': {
                    'herbs': ['Guggulu', 'Ashwagandha', 'Dashamool'],
                    'treatments': ['Warm oil massage', 'Kati Basti', 'Steam therapy'],
                    'diet': ['Warm soups', 'Ghee', 'Avoid cold foods'],
                    'lifestyle': ['Gentle movement', 'Stay warm', 'Avoid overexertion'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana - Vatavyadhi'
                }
            },
            'skin_health': {
                'pitta': {
                    'herbs': ['Neem', 'Manjistha', 'Sariva'],
                    'treatments': ['Blood purification', 'Virechana', 'Cooling oils'],
                    'diet': ['Bitter greens', 'Cooling foods', 'Avoid spicy/oily'],
                    'lifestyle': ['Avoid sun exposure', 'Use natural products'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana - Kushtha'
                }
            },
            'weight_management': {
                'kapha': {
                    'herbs': ['Triphala', 'Guggulu', 'Garcinia'],
                    'treatments': ['Udvartana (dry powder massage)', 'Steam'],
                    'diet': ['Light meals', 'Fasting', 'Avoid sweets/dairy'],
                    'lifestyle': ['Daily vigorous exercise', 'Early rising', 'Varied routine'],
                    'classical_reference': 'Charaka Samhita, Sutrasthana - Sthaulya'
                }
            },
            'respiratory': {
                'kapha': {
                    'herbs': ['Sitopaladi', 'Trikatu', 'Tulsi', 'Licorice'],
                    'treatments': ['Steam inhalation', 'Nasya', 'Chest massage'],
                    'diet': ['Warm foods', 'Honey', 'Avoid dairy/cold'],
                    'lifestyle': ['Stay warm', 'Pranayama', 'Avoid dampness'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana - Kasa'
                }
            },
            'heart_health': {
                'general': {
                    'herbs': ['Arjuna', 'Ashwagandha', 'Brahmi'],
                    'treatments': ['Hridya Basti', 'Stress reduction'],
                    'diet': ['Heart-healthy foods', 'Garlic', 'Reduce salt'],
                    'lifestyle': ['Regular exercise', 'Yoga', 'Stress management'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana - Hridroga'
                }
            },
            'diabetes': {
                'general': {
                    'herbs': ['Gudmar (Gymnema)', 'Karela', 'Neem', 'Triphala'],
                    'treatments': ['Panchakarma', 'Udwartana'],
                    'diet': ['Bitter vegetables', 'Low glycemic', 'Avoid sweets'],
                    'lifestyle': ['Regular exercise', 'Stress management', 'Regular meals'],
                    'classical_reference': 'Charaka Samhita, Chikitsa Sthana - Prameha'
                }
            }
        }
    
    def _load_herbs(self) -> Dict:
        """Comprehensive herb database"""
        return {
            'ashwagandha': {
                'sanskrit': 'Ashwagandha',
                'botanical': 'Withania somnifera',
                'properties': {'rasa': 'Bitter, Astringent', 'virya': 'Heating', 'vipaka': 'Sweet'},
                'doshas': {'vata': 'reduces', 'pitta': 'neutral', 'kapha': 'reduces'},
                'benefits': ['Stress relief', 'Strength building', 'Sleep support', 'Immune boost'],
                'contraindications': ['Pregnancy', 'Hyperthyroidism'],
                'dosage': '300-600mg twice daily'
            },
            'brahmi': {
                'sanskrit': 'Brahmi',
                'botanical': 'Bacopa monnieri',
                'properties': {'rasa': 'Bitter', 'virya': 'Cooling', 'vipaka': 'Sweet'},
                'doshas': {'vata': 'reduces', 'pitta': 'reduces', 'kapha': 'reduces'},
                'benefits': ['Mental clarity', 'Memory support', 'Stress relief', 'Focus'],
                'contraindications': ['Pregnancy (high doses)'],
                'dosage': '300-450mg daily'
            },
            'triphala': {
                'sanskrit': 'Triphala',
                'botanical': 'Amalaki, Bibhitaki, Haritaki blend',
                'properties': {'rasa': 'All except salty', 'virya': 'Neutral', 'vipaka': 'Sweet'},
                'doshas': {'vata': 'reduces', 'pitta': 'reduces', 'kapha': 'reduces'},
                'benefits': ['Digestion', 'Detox', 'Eye health', 'Immunity'],
                'contraindications': ['Pregnancy', 'Diarrhea'],
                'dosage': '500mg-1g before bed'
            },
            'turmeric': {
                'sanskrit': 'Haridra',
                'botanical': 'Curcuma longa',
                'properties': {'rasa': 'Bitter, Pungent', 'virya': 'Heating', 'vipaka': 'Pungent'},
                'doshas': {'vata': 'reduces', 'pitta': 'increases slightly', 'kapha': 'reduces'},
                'benefits': ['Anti-inflammatory', 'Antioxidant', 'Liver support', 'Joint health'],
                'contraindications': ['Gallstones', 'Blood thinners'],
                'dosage': '500mg-2g daily with black pepper'
            },
            'tulsi': {
                'sanskrit': 'Tulsi',
                'botanical': 'Ocimum sanctum',
                'properties': {'rasa': 'Pungent, Bitter', 'virya': 'Heating', 'vipaka': 'Pungent'},
                'doshas': {'vata': 'reduces', 'pitta': 'increases slightly', 'kapha': 'reduces'},
                'benefits': ['Immunity', 'Respiratory health', 'Stress relief', 'Antioxidant'],
                'contraindications': ['Blood thinning medications'],
                'dosage': '300-600mg or as tea'
            },
            'guduchi': {
                'sanskrit': 'Guduchi',
                'botanical': 'Tinospora cordifolia',
                'properties': {'rasa': 'Bitter, Astringent', 'virya': 'Heating', 'vipaka': 'Sweet'},
                'doshas': {'vata': 'reduces', 'pitta': 'reduces', 'kapha': 'reduces'},
                'benefits': ['Immunity', 'Liver support', 'Fever', 'Anti-inflammatory'],
                'contraindications': ['Autoimmune conditions (consult doctor)'],
                'dosage': '300-500mg twice daily'
            }
        }
    
    def _load_yoga(self) -> Dict:
        """Yoga practices by dosha and condition"""
        return {
            'vata': {
                'asanas': ['Tadasana', 'Virabhadrasana', 'Paschimottanasana', 'Balasana', 'Savasana'],
                'pranayama': ['Nadi Shodhana', 'Ujjayi', 'Bhramari'],
                'pace': 'Slow, steady, grounding',
                'focus': 'Stability, warmth, calming'
            },
            'pitta': {
                'asanas': ['Chandrasana', 'Ardha Matsyendrasana', 'Forward bends', 'Restorative poses'],
                'pranayama': ['Sheetali', 'Sheetkari', 'Chandra Bhedana'],
                'pace': 'Moderate, cooling, non-competitive',
                'focus': 'Cooling, surrendering, relaxation'
            },
            'kapha': {
                'asanas': ['Surya Namaskar', 'Backbends', 'Inversions', 'Standing poses'],
                'pranayama': ['Kapalabhati', 'Bhastrika', 'Surya Bhedana'],
                'pace': 'Vigorous, warming, energizing',
                'focus': 'Stimulation, movement, lightness'
            }
        }
    
    def _load_diet(self) -> Dict:
        """Dietary guidelines by dosha"""
        return {
            'vata': {
                'favor': ['Warm foods', 'Cooked vegetables', 'Sweet fruits', 'Whole grains', 'Ghee', 'Nuts', 'Warm spices'],
                'reduce': ['Cold foods', 'Raw vegetables', 'Dried fruits', 'Beans', 'Caffeine'],
                'tastes_favor': ['Sweet', 'Sour', 'Salty'],
                'tastes_reduce': ['Bitter', 'Astringent', 'Pungent'],
                'meal_timing': 'Regular, 3 meals, warm breakfast'
            },
            'pitta': {
                'favor': ['Cooling foods', 'Sweet fruits', 'Leafy greens', 'Coconut', 'Dairy', 'Mint'],
                'reduce': ['Spicy foods', 'Sour foods', 'Fermented foods', 'Alcohol', 'Coffee'],
                'tastes_favor': ['Sweet', 'Bitter', 'Astringent'],
                'tastes_reduce': ['Sour', 'Salty', 'Pungent'],
                'meal_timing': 'Regular, largest meal at noon'
            },
            'kapha': {
                'favor': ['Light foods', 'Spices', 'Leafy greens', 'Beans', 'Honey', 'Bitter vegetables'],
                'reduce': ['Heavy foods', 'Dairy', 'Sweets', 'Fried foods', 'Cold drinks'],
                'tastes_favor': ['Pungent', 'Bitter', 'Astringent'],
                'tastes_reduce': ['Sweet', 'Sour', 'Salty'],
                'meal_timing': 'Light breakfast, main meal at noon, early light dinner'
            }
        }
    
    def retrieve_remedies(self, condition: str, dosha: str) -> Dict:
        """Retrieve relevant remedies for a condition and dosha"""
        condition_lower = condition.lower()
        dosha_lower = dosha.lower().split('-')[0]  # Handle dual doshas
        
        # Find matching condition
        remedies = None
        for key in self.remedies_db:
            if key in condition_lower or condition_lower in key:
                condition_data = self.remedies_db[key]
                if dosha_lower in condition_data:
                    remedies = condition_data[dosha_lower]
                elif 'general' in condition_data:
                    remedies = condition_data['general']
                break
        
        if not remedies:
            # Default to general immunity
            remedies = self.remedies_db.get('immunity', {}).get('general', {})
        
        return {
            'condition': condition,
            'dosha': dosha,
            'remedies': remedies,
            'disclaimer': 'These are traditional recommendations. Consult an Ayurvedic practitioner before use.'
        }
    
    def get_herb_info(self, herb_name: str) -> Optional[Dict]:
        """Get detailed information about a specific herb"""
        herb_lower = herb_name.lower()
        return self.herbs_db.get(herb_lower)
    
    def get_yoga_recommendations(self, dosha: str) -> Dict:
        """Get yoga recommendations for a dosha"""
        dosha_lower = dosha.lower().split('-')[0]
        return self.yoga_db.get(dosha_lower, self.yoga_db['vata'])
    
    def get_diet_guidelines(self, dosha: str) -> Dict:
        """Get dietary guidelines for a dosha"""
        dosha_lower = dosha.lower().split('-')[0]
        return self.diet_db.get(dosha_lower, self.diet_db['vata'])
    
    def generate_personalized_plan(self, prakriti: str, conditions: List[str], 
                                   symptoms: List[str]) -> Dict:
        """Generate a comprehensive personalized Ayurvedic plan"""
        primary_dosha = prakriti.split('-')[0].lower() if '-' in prakriti else prakriti.lower()
        
        plan = {
            'prakriti': prakriti,
            'primary_dosha': primary_dosha,
            'diet': self.get_diet_guidelines(prakriti),
            'yoga': self.get_yoga_recommendations(prakriti),
            'daily_routine': self._get_dinacharya(primary_dosha),
            'condition_specific': [],
            'herbs_recommended': [],
            'precautions': []
        }
        
        # Add condition-specific remedies
        for condition in conditions + symptoms:
            remedy = self.retrieve_remedies(condition, prakriti)
            if remedy['remedies']:
                plan['condition_specific'].append(remedy)
                # Collect herbs
                if 'herbs' in remedy['remedies']:
                    for herb in remedy['remedies']['herbs']:
                        if herb.lower() in self.herbs_db:
                            herb_info = self.herbs_db[herb.lower()]
                            if herb_info not in plan['herbs_recommended']:
                                plan['herbs_recommended'].append({
                                    'name': herb,
                                    'info': herb_info
                                })
        
        return plan
    
    def _get_dinacharya(self, dosha: str) -> Dict:
        """Daily routine recommendations by dosha"""
        routines = {
            'vata': {
                'wake_time': '6:00 AM',
                'morning_routine': [
                    'Warm water with lemon',
                    'Oil pulling with sesame oil',
                    'Self-massage (Abhyanga) with warm oil',
                    'Gentle yoga and meditation'
                ],
                'meal_times': {'breakfast': '7:30 AM', 'lunch': '12:00 PM', 'dinner': '6:00 PM'},
                'evening_routine': ['Light walk', 'Warm bath', 'Early bedtime by 10 PM'],
                'sleep_time': '10:00 PM'
            },
            'pitta': {
                'wake_time': '5:30 AM',
                'morning_routine': [
                    'Cool water',
                    'Coconut oil massage',
                    'Cooling yoga',
                    'Meditation by water'
                ],
                'meal_times': {'breakfast': '7:00 AM', 'lunch': '12:00 PM (main meal)', 'dinner': '6:30 PM'},
                'evening_routine': ['Moonlight walk', 'Creative activity', 'Cool shower'],
                'sleep_time': '10:30 PM'
            },
            'kapha': {
                'wake_time': '5:00 AM',
                'morning_routine': [
                    'Warm water with honey',
                    'Dry brushing',
                    'Vigorous exercise',
                    'Stimulating pranayama'
                ],
                'meal_times': {'breakfast': '8:00 AM (light)', 'lunch': '12:00 PM (main)', 'dinner': '5:30 PM (light)'},
                'evening_routine': ['Active evening', 'Varied activities', 'Avoid napping'],
                'sleep_time': '10:00 PM'
            }
        }
        return routines.get(dosha, routines['vata'])


# Singleton instance
_knowledge_base = None

def get_ayurveda_knowledge_base() -> AyurvedaKnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = AyurvedaKnowledgeBase()
    return _knowledge_base
