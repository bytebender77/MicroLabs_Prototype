from typing import Optional, Dict
from enum import Enum

class TemperatureCategory(str, Enum):
    NORMAL = "normal"
    WARM = "warm"
    FEVER = "fever"
    HIGH_FEVER = "high_fever"
    VERY_HIGH_FEVER = "very_high_fever"
    CRITICAL = "critical"

class TemperatureHandler:
    """
    Smart temperature handler for users with/without thermometer.
    Accessible for all economic backgrounds.
    """
    
    # Temperature ranges in Celsius
    TEMP_RANGES = {
        TemperatureCategory.NORMAL: (36.1, 37.2),
        TemperatureCategory.WARM: (37.3, 38.0),
        TemperatureCategory.FEVER: (38.1, 38.9),
        TemperatureCategory.HIGH_FEVER: (39.0, 39.9),
        TemperatureCategory.VERY_HIGH_FEVER: (40.0, 41.0),
        TemperatureCategory.CRITICAL: (41.1, 45.0),
    }
    
    # Descriptive symptoms for users without thermometer
    DESCRIPTIVE_MAPPING = {
        "feeling_normal": TemperatureCategory.NORMAL,
        "slightly_warm": TemperatureCategory.WARM,
        "hot_to_touch": TemperatureCategory.FEVER,
        "very_hot_sweating": TemperatureCategory.HIGH_FEVER,
        "burning_up": TemperatureCategory.VERY_HIGH_FEVER,
        "extreme_heat_confusion": TemperatureCategory.CRITICAL,
    }
    
    @classmethod
    def categorize_temperature(
        cls, 
        temp_celsius: Optional[float] = None,
        descriptive: Optional[str] = None
    ) -> Dict:
        """
        Categorize temperature from numeric value OR description.
        """
        if temp_celsius is not None:
            category = cls._categorize_numeric(temp_celsius)
            return {
                "category": category,
                "temperature_c": temp_celsius,
                "temperature_f": cls._celsius_to_fahrenheit(temp_celsius),
                "input_type": "numeric",
                "description": cls._get_description(category),
                "urgency": cls._get_urgency(category)
            }
        
        elif descriptive is not None:
            category = cls.DESCRIPTIVE_MAPPING.get(
                descriptive, 
                TemperatureCategory.FEVER
            )
            return {
                "category": category,
                "temperature_c": cls._estimate_temperature(category),
                "temperature_f": None,
                "input_type": "descriptive",
                "description": cls._get_description(category),
                "urgency": cls._get_urgency(category)
            }
        
        return {
            "category": TemperatureCategory.FEVER,
            "input_type": "unknown",
            "urgency": "moderate"
        }
    
    @classmethod
    def _categorize_numeric(cls, temp: float) -> TemperatureCategory:
        for category, (low, high) in cls.TEMP_RANGES.items():
            if low <= temp <= high:
                return category
        if temp < 36.1:
            return TemperatureCategory.NORMAL
        return TemperatureCategory.CRITICAL
    
    @staticmethod
    def _celsius_to_fahrenheit(c: float) -> float:
        return round((c * 9/5) + 32, 1)
    
    @classmethod
    def _estimate_temperature(cls, category: TemperatureCategory) -> float:
        """Estimate mid-range temperature for category"""
        if category in cls.TEMP_RANGES:
            low, high = cls.TEMP_RANGES[category]
            return round((low + high) / 2, 1)
        return 38.5
    
    @staticmethod
    def _get_description(category: TemperatureCategory) -> str:
        descriptions = {
            TemperatureCategory.NORMAL: "Normal body temperature",
            TemperatureCategory.WARM: "Slightly elevated, low-grade fever",
            TemperatureCategory.FEVER: "Moderate fever",
            TemperatureCategory.HIGH_FEVER: "High fever - needs attention",
            TemperatureCategory.VERY_HIGH_FEVER: "Very high fever - urgent care needed",
            TemperatureCategory.CRITICAL: "Critical temperature - EMERGENCY",
        }
        return descriptions.get(category, "Fever present")
    
    @staticmethod
    def _get_urgency(category: TemperatureCategory) -> str:
        urgency_map = {
            TemperatureCategory.NORMAL: "none",
            TemperatureCategory.WARM: "low",
            TemperatureCategory.FEVER: "moderate",
            TemperatureCategory.HIGH_FEVER: "high",
            TemperatureCategory.VERY_HIGH_FEVER: "urgent",
            TemperatureCategory.CRITICAL: "emergency",
        }
        return urgency_map.get(category, "moderate")
    
    @staticmethod
    def get_temperature_questions() -> Dict:
        """
        Return user-friendly temperature questions
        """
        return {
            "numeric_question": "What is your body temperature? (in °C or °F)",
            "descriptive_question": "If you don't have a thermometer, how does your body feel?",
            "descriptive_options": [
                {
                    "value": "feeling_normal",
                    "label": "Feeling normal",
                    "emoji": "😊"
                },
                {
                    "value": "slightly_warm",
                    "label": "Slightly warm/uncomfortable",
                    "emoji": "😐"
                },
                {
                    "value": "hot_to_touch",
                    "label": "Hot to touch, sweating a bit",
                    "emoji": "🥵"
                },
                {
                    "value": "very_hot_sweating",
                    "label": "Very hot, sweating heavily",
                    "emoji": "😰"
                },
                {
                    "value": "burning_up",
                    "label": "Burning up, very uncomfortable",
                    "emoji": "🔥"
                },
                {
                    "value": "extreme_heat_confusion",
                    "label": "Extreme heat, feeling confused",
                    "emoji": "🚨"
                }
            ]
        }