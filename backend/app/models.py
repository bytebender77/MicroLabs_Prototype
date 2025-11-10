"""Data models for HealthGuide"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime
from enum import Enum


class TriageLevel(str, Enum):
    """Triage level classification"""
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    SELF_CARE = "SELF_CARE"
    FOLLOW_UP = "FOLLOW_UP"


class Message(BaseModel):
    """Chat message model"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


class TriageResult(BaseModel):
    """Triage assessment result"""
    triage_level: TriageLevel
    escalate: bool
    summary: str
    recommended_next_steps: List[str]
    next_question: Optional[str] = None
    red_flag_detected: bool = False
    red_flag_symptom: Optional[str] = None


class SymptomData(BaseModel):
    """Structured symptom data from symptom selector"""
    symptoms: List[str] = []
    by_category: Optional[Dict[str, List[str]]] = None
    emergency_detected: bool = False
    total_selected: int = 0
    language: Optional[str] = "en"


class ConversationRequest(BaseModel):
    """Request model for triage endpoint"""
    session_id: str
    message: str
    conversation_history: List[Message] = []
    llm_provider: Optional[str] = "openai"  # openai or gemini
    symptom_data: Optional[SymptomData] = None  # Optional structured symptom data


class ConversationResponse(BaseModel):
    """Response model for triage endpoint"""
    session_id: str
    message: str
    triage_result: Optional[TriageResult] = None
    conversation_complete: bool = False


# ===================== PROVIDER MODELS =====================

class Provider(BaseModel):
    """Healthcare provider model"""
    id: str
    name: str
    type: str  # clinic, pharmacy, hospital
    address: str
    phone: Optional[str] = None
    distance: Optional[float] = None  # distance in km
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None  # optional: future support for Google reviews
    open_now: Optional[bool] = None
    maps_url: Optional[str] = None  # Google Maps or OpenStreetMap link


class ProviderRequest(BaseModel):
    """Request model for providers endpoint"""
    latitude: float
    longitude: float
    radius: int = 5  # km search radius
    provider_type: Optional[str] = None  # e.g., clinic, hospital, pharmacy
    use_live_data: Optional[bool] = True  # flag for live map API integration


class SummaryResponse(BaseModel):
    """Response model for summary endpoint"""
    session_id: str
    summary: str
    triage_level: TriageLevel
    recommended_next_steps: List[str]
    conversation_count: int


# ===================== TEMPERATURE MODELS =====================

class TemperatureRequest(BaseModel):
    """Request model for temperature assessment"""
    session_id: str
    temperature_celsius: Optional[float] = None
    temperature_fahrenheit: Optional[float] = None
    descriptive: Optional[str] = None  # e.g., "hot_to_touch", "burning_up"


class TemperatureResponse(BaseModel):
    """Response model for temperature assessment"""
    category: str
    temperature_c: Optional[float] = None
    temperature_f: Optional[float] = None
    input_type: str
    description: str
    urgency: str


# ===================== DISEASE DETECTION MODELS =====================

class DiseaseDetectionRequest(BaseModel):
    """Request model for disease detection"""
    symptoms: List[str]
    temperature_category: Optional[str] = None
    duration_days: Optional[int] = None
    additional_context: Optional[Dict] = None


class DiseaseMatch(BaseModel):
    """Disease match result"""
    disease: str
    disease_id: str
    match_score: float
    matching_symptoms: List[str]
    severity: str
    home_care: List[str]
    when_to_see_doctor: List[str]
    diagnostic_tests: Optional[List[str]] = None
    red_flags: Optional[List[str]] = None


class DiseaseDetectionResponse(BaseModel):
    """Response model for disease detection"""
    probable_causes: List[DiseaseMatch]
    medication_suggestions: Optional[Dict] = None


# ===================== GEOLOCATION MODELS =====================

class GeolocationProviderRequest(BaseModel):
    """Request model for geolocation providers"""
    latitude: float
    longitude: float
    radius_km: int = 5
    provider_type: Optional[str] = "hospital"  # hospital, clinic, pharmacy
    limit: int = 10
    session_id: Optional[str] = None
    triage_level: Optional[str] = None
    symptoms: Optional[List[str]] = None


class GeolocationProvider(BaseModel):
    """Enhanced provider model with geolocation data"""
    name: str
    address: str
    type: str
    distance_km: float
    latitude: float
    longitude: float
    rating: Optional[float] = None
    total_ratings: Optional[int] = None
    open_now: Optional[bool] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    place_id: Optional[str] = None
    source: Optional[str] = None


# ===================== MEDICATION MODELS =====================

class MedicationReminderRequest(BaseModel):
    """Request model for medication reminder"""
    session_id: str
    medication_name: str
    dosage: str
    frequency: str  # e.g., "every_6_hours", "daily", "2x_daily"
    duration_days: int
    notes: Optional[str] = None


class MedicationReminderResponse(BaseModel):
    """Response model for medication reminder"""
    id: int
    medication_name: str
    dosage: str
    frequency: str
    frequency_label: str
    duration_days: int
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = None
    schedule: List[Dict]
    next_dose: Optional[Dict] = None
    total_doses: int


# ===================== ANALYTICS MODELS =====================

class AnalyticsRequest(BaseModel):
    """Request model for analytics"""
    days: int = 7
    region: Optional[str] = None
    country: str = "India"


class AnalyticsResponse(BaseModel):
    """Response model for analytics"""
    summary_stats: Dict
    geographic_trends: List[Dict]
    disease_distribution: Dict
    time_series_data: List[Dict]
    potential_outbreaks: List[Dict]
