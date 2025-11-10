from typing import List, Dict, Optional
import json
from pathlib import Path

class DiseaseDetector:
    """
    AI-powered symptom-to-disease mapping for fever cases.
    Identifies probable causes: viral fever, dengue, typhoid, malaria, etc.
    """
    
    def __init__(self):
        self.disease_db = self._load_disease_database()
    
    def _load_disease_database(self) -> Dict:
        """Load disease symptom mappings"""
        # This would be a comprehensive database
        return {
            "viral_fever": {
                "name": "Viral Fever",
                "symptoms": [
                    "fever", "body_ache", "fatigue", "headache", 
                    "runny_nose", "sore_throat", "cough"
                ],
                "duration_pattern": "3-7 days",
                "severity": "mild_to_moderate",
                "red_flags": [],
                "home_care": [
                    "Rest adequately",
                    "Drink plenty of fluids",
                    "Take paracetamol for fever (if no contraindications)",
                    "Monitor temperature regularly"
                ],
                "when_to_see_doctor": [
                    "Fever persists beyond 3-4 days",
                    "Symptoms worsen",
                    "Difficulty breathing"
                ]
            },
            "dengue": {
                "name": "Dengue Fever",
                "symptoms": [
                    "high_fever", "severe_headache", "pain_behind_eyes",
                    "joint_pain", "muscle_pain", "rash", "nausea",
                    "bleeding_gums", "easy_bruising"
                ],
                "duration_pattern": "2-7 days high fever",
                "severity": "moderate_to_severe",
                "red_flags": [
                    "severe_abdominal_pain", "persistent_vomiting",
                    "bleeding", "difficulty_breathing", "cold_clammy_skin"
                ],
                "home_care": [
                    "⚠️ MUST see doctor for diagnosis",
                    "Drink plenty of fluids (ORS, coconut water)",
                    "Complete bed rest",
                    "Monitor platelet count regularly",
                    "❌ Avoid aspirin and ibuprofen (bleeding risk)"
                ],
                "when_to_see_doctor": [
                    "Immediately - dengue requires medical monitoring"
                ],
                "diagnostic_tests": ["Complete Blood Count", "NS1 Antigen", "Dengue IgM/IgG"]
            },
            "typhoid": {
                "name": "Typhoid Fever",
                "symptoms": [
                    "sustained_high_fever", "weakness", "stomach_pain",
                    "headache", "loss_of_appetite", "constipation_or_diarrhea",
                    "rose_spots_rash"
                ],
                "duration_pattern": "Fever increases gradually over days",
                "severity": "moderate_to_severe",
                "red_flags": [
                    "severe_abdominal_pain", "confusion", "intestinal_bleeding"
                ],
                "home_care": [
                    "⚠️ REQUIRES antibiotic treatment",
                    "See doctor immediately",
                    "Drink clean, boiled water only",
                    "Easily digestible food"
                ],
                "when_to_see_doctor": [
                    "Immediately - typhoid needs antibiotics"
                ],
                "diagnostic_tests": ["Widal Test", "Blood Culture", "Typhi-dot"]
            },
            "malaria": {
                "name": "Malaria",
                "symptoms": [
                    "cyclical_fever", "chills", "sweating", "headache",
                    "nausea", "vomiting", "muscle_pain", "fatigue"
                ],
                "duration_pattern": "Fever spikes every 48-72 hours",
                "severity": "moderate_to_severe",
                "red_flags": [
                    "confusion", "seizures", "difficulty_breathing",
                    "severe_anemia", "dark_urine"
                ],
                "home_care": [
                    "⚠️ REQUIRES antimalarial medication",
                    "See doctor immediately",
                    "Prevent mosquito bites"
                ],
                "when_to_see_doctor": [
                    "Immediately - malaria needs specific treatment"
                ],
                "diagnostic_tests": ["Blood Smear", "Rapid Diagnostic Test (RDT)"]
            },
            "influenza": {
                "name": "Flu (Influenza)",
                "symptoms": [
                    "sudden_high_fever", "dry_cough", "body_ache",
                    "fatigue", "headache", "sore_throat", "chills"
                ],
                "duration_pattern": "3-7 days",
                "severity": "moderate",
                "home_care": [
                    "Rest and isolate",
                    "Fluids",
                    "Antiviral medication if prescribed within 48 hours",
                    "Paracetamol for fever"
                ],
                "when_to_see_doctor": [
                    "High-risk groups (elderly, pregnant, chronic illness)",
                    "Symptoms worsen after 3 days"
                ]
            },
            "covid19": {
                "name": "COVID-19",
                "symptoms": [
                    "fever", "dry_cough", "fatigue", "loss_of_taste_smell",
                    "body_ache", "sore_throat", "difficulty_breathing"
                ],
                "duration_pattern": "Varies (5-14 days)",
                "severity": "mild_to_critical",
                "red_flags": [
                    "difficulty_breathing", "chest_pain", "confusion",
                    "bluish_lips", "oxygen_saturation_below_94"
                ],
                "home_care": [
                    "Isolate immediately",
                    "Get tested (RT-PCR/RAT)",
                    "Monitor oxygen levels",
                    "Rest and fluids",
                    "Consult doctor if breathing difficulty"
                ],
                "when_to_see_doctor": [
                    "Breathing difficulty",
                    "Oxygen < 94%",
                    "High-risk individuals"
                ]
            },
            "urinary_tract_infection": {
                "name": "Urinary Tract Infection (UTI)",
                "symptoms": [
                    "fever", "burning_urination", "frequent_urination",
                    "lower_abdominal_pain", "cloudy_urine", "back_pain"
                ],
                "severity": "moderate",
                "home_care": [
                    "Drink plenty of water",
                    "⚠️ Requires antibiotic treatment",
                    "See doctor for proper diagnosis"
                ],
                "diagnostic_tests": ["Urine Culture", "Urinalysis"]
            }
        }
    
    def detect_probable_causes(
        self,
        symptoms: List[str],
        temperature_category: str,
        duration_days: Optional[int] = None,
        additional_context: Dict = None
    ) -> List[Dict]:
        """
        Analyze symptoms and return probable disease causes ranked by likelihood.
        """
        matched_diseases = []
        
        # Normalize symptoms
        symptoms_normalized = [s.lower().replace(" ", "_") for s in symptoms]
        
        for disease_id, disease_data in self.disease_db.items():
            disease_symptoms = disease_data.get("symptoms", [])
            
            # Calculate match score
            matching_symptoms = set(symptoms_normalized) & set(disease_symptoms)
            match_score = len(matching_symptoms) / len(disease_symptoms) if disease_symptoms else 0
            
            # Boost score for high-priority diseases
            if disease_id in ["dengue", "typhoid", "malaria"] and match_score > 0.3:
                match_score += 0.1
            
            if match_score > 0.2:  # Threshold for consideration
                matched_diseases.append({
                    "disease": disease_data["name"],
                    "disease_id": disease_id,
                    "match_score": round(match_score * 100, 1),
                    "matching_symptoms": list(matching_symptoms),
                    "severity": disease_data.get("severity", "moderate"),
                    "home_care": disease_data.get("home_care", []),
                    "when_to_see_doctor": disease_data.get("when_to_see_doctor", []),
                    "diagnostic_tests": disease_data.get("diagnostic_tests", []),
                    "red_flags": disease_data.get("red_flags", [])
                })
        
        # Sort by match score
        matched_diseases.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Return top 3 probable causes
        return matched_diseases[:3]
    
    def get_home_care_recommendations(self, disease_id: str) -> List[str]:
        """Get specific home care recommendations"""
        disease = self.disease_db.get(disease_id, {})
        return disease.get("home_care", [
            "Rest adequately",
            "Stay hydrated",
            "Monitor temperature",
            "Consult doctor if symptoms worsen"
        ])
    
    def get_medication_suggestions(
        self, 
        disease_id: str,
        age_group: str,
        has_allergies: bool = False
    ) -> Dict:
        """
        Safe medication suggestions (OTC only, with disclaimers)
        """
        base_recommendations = {
            "fever_reducer": {
                "name": "Paracetamol (Acetaminophen)",
                "dosage_adult": "500-1000mg every 6 hours (max 4000mg/day)",
                "dosage_child": "10-15mg/kg every 6 hours",
                "notes": "Safe for most people. Avoid if liver disease."
            },
            "hydration": {
                "recommendation": "ORS (Oral Rehydration Solution)",
                "amount": "Small sips frequently, aim for 2-3 liters/day"
            }
        }
        
        # Disease-specific additions
        disease_specific = {
            "dengue": {
                "avoid": ["Aspirin", "Ibuprofen", "NSAIDs"],
                "reason": "Increased bleeding risk",
                "special_care": "Monitor platelet count"
            },
            "viral_fever": {
                "safe_otc": ["Paracetamol only"],
                "avoid_antibiotics": True
            }
        }
        
        return {
            "general": base_recommendations,
            "specific": disease_specific.get(disease_id, {}),
            "disclaimer": "⚠️ This is general guidance. Consult a doctor before taking any medication, especially for children, pregnant women, or people with existing conditions."
        }