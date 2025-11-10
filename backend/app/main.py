"""Main FastAPI application for HealthGuide"""
from fastapi import FastAPI, HTTPException, Depends  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]
from typing import List, Optional
import uuid
from datetime import datetime
from pydantic import BaseModel
import requests
import json

from app.config import settings
from app.models import (
    ConversationRequest, ConversationResponse, TriageResult, TriageLevel,
    ProviderRequest, Provider, SummaryResponse, Message,
    TemperatureRequest, TemperatureResponse,
    DiseaseDetectionRequest, DiseaseDetectionResponse, DiseaseMatch,
    GeolocationProviderRequest, GeolocationProvider,
    MedicationReminderRequest, MedicationReminderResponse,
    AnalyticsRequest, AnalyticsResponse
)
from app.database import (
    get_db, init_db, save_conversation, get_conversation, 
    save_temperature, get_temperature_history, FeverTrendDB
)
from app.llm_service import get_llm_service, get_system_prompt
from app.red_flags import check_red_flags, get_red_flag_response
from app.providers import get_providers
from app.fever_diseases import identify_fever_type, get_disease_recommendations
from app.services.temperature_handler import TemperatureHandler
from app.services.disease_detector import DiseaseDetector
from app.services.geolocation import GeolocationService
from app.services.medication_service import MedicationService
from app.services.analytics_service import AnalyticsService


def normalize_message_dict(msg_dict: dict) -> dict:
    """Normalize a message dictionary to ensure all values are JSON serializable"""
    normalized = {}
    for key, value in msg_dict.items():
        if isinstance(value, datetime):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = value
    return normalized


# Initialize FastAPI app
app = FastAPI(
    title="HealthGuide - Fever Helpline API",
    description="AI-powered fever triage and guidance system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "HealthGuide API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "HealthGuide API"}


# ------------------- TRIAGE ENDPOINT ------------------- #
@app.post("/api/triage", response_model=ConversationResponse)
async def triage(
    request: ConversationRequest,
    db: Session = Depends(get_db)
):
    """
    Main triage endpoint that processes user messages and provides guidance.
    """
    try:
        provider = request.llm_provider or settings.llm_provider
        llm_service = get_llm_service(provider=provider)
        enhanced_message = request.message

        if request.symptom_data:
            symptom_data = request.symptom_data
            if symptom_data.emergency_detected:
                enhanced_message = f"EMERGENCY SYMPTOMS DETECTED: {request.message}"
            if symptom_data.symptoms:
                symptom_list = ", ".join(symptom_data.symptoms)
                # Keep the message natural - don't add extra context that makes it sound like a query
                enhanced_message = request.message  # Use original message, symptoms are in symptom_data

        # ----------------- RED FLAG DETECTION (Frontend-driven) -----------------
        emergency_flag = request.symptom_data.emergency_detected if request.symptom_data else False

        # Only perform red flag check if the frontend marked an emergency
        red_flag = check_red_flags(request.message, emergency_flag) or check_red_flags(enhanced_message, emergency_flag)

        # Fallback safety: if emergency flag true but no keyword matched, still mark as emergency
        if emergency_flag and not red_flag:
            red_flag = "Emergency symptoms selected via symptom selector"


        if red_flag:
            conversation_dicts = []
            for msg in request.conversation_history:
                if isinstance(msg, dict):
                    conversation_dicts.append(normalize_message_dict(msg))
                elif isinstance(msg, Message):
                    ts = getattr(msg, "timestamp", datetime.now()).isoformat()
                    conversation_dicts.append({
                        "role": msg.role, "content": msg.content, "timestamp": ts
                    })
            messages = conversation_dicts + [
                {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": get_red_flag_response(red_flag), "timestamp": datetime.now().isoformat()}
            ]
            save_conversation(
                db=db,
                session_id=request.session_id,
                messages=messages,
                triage_level=TriageLevel.EMERGENCY.value,
                red_flag=red_flag
            )
            return ConversationResponse(
                session_id=request.session_id,
                message=get_red_flag_response(red_flag),
                triage_result=TriageResult(
                    triage_level=TriageLevel.EMERGENCY,
                    escalate=True,
                    summary=f"Red flag symptom detected: {red_flag}",
                    recommended_next_steps=[
                        "Call emergency services immediately",
                        "Go to the nearest emergency room",
                        "Do not delay seeking medical attention"
                    ],
                    red_flag_detected=True,
                    red_flag_symptom=red_flag
                ),
                conversation_complete=True
            )

        messages = []
        for msg in request.conversation_history:
            if isinstance(msg, dict):
                messages.append(Message(role=msg.get("role", "user"), content=msg.get("content", "")))
            elif isinstance(msg, Message):
                messages.append(msg)
            else:
                messages.append(Message(role=getattr(msg, "role", "user"), content=getattr(msg, "content", "")))

        messages.append(Message(role="user", content=request.message))
        conversation_history = [{"role": m.role, "content": m.content} for m in messages]
        
        # For triage assessment, use the original message (symptoms are already in the message)
        # The symptom_data is used for context but the message itself should be natural
        triage_message = request.message  # Use original message for assessment
        triage_result = llm_service.assess_triage(conversation_history, triage_message)

        disease_analysis = identify_fever_type(triage_message)
        if disease_analysis["confidence"] > 0.3:
            disease_recommendations = get_disease_recommendations(disease_analysis["likely_type"])
            if disease_recommendations:
                triage_result.recommended_next_steps = disease_recommendations + triage_result.recommended_next_steps
                triage_result.summary = (
                    f"{triage_result.summary} "
                    f"(Possible {disease_analysis['likely_type'].upper()} - "
                    f"{disease_analysis['confidence']*100:.0f}% confidence)"
                )

        if triage_result.red_flag_detected:
            response_message = get_red_flag_response(triage_result.red_flag_symptom or "red flag symptom")
            conversation_complete = True
        else:
            # Check if this is an initial symptom submission with structured data
            has_structured_symptoms = request.symptom_data and request.symptom_data.symptoms and len(request.symptom_data.symptoms) > 0
            
            if has_structured_symptoms:
                # For structured symptom submissions, provide direct assessment
                # Build a comprehensive assessment prompt
                symptom_list = ", ".join(request.symptom_data.symptoms)
                
                # Create assessment context for LLM
                assessment_context = f"""Patient Report:
Symptoms: {symptom_list}
Emergency symptoms detected: {'Yes' if request.symptom_data.emergency_detected else 'No'}
Total symptoms: {request.symptom_data.total_selected}

Instructions:
- Provide a clear, empathetic assessment of the patient's condition
- Give immediate recommendations (home care, when to see a doctor)
- Mention probable causes if identifiable from symptoms
- Provide actionable next steps
- Be reassuring but thorough
- DO NOT ask questions - provide guidance directly based on the symptoms

Keep the response conversational and helpful."""
                
                # Use the system prompt but with assessment context
                assessment_messages = [
                    Message(role="system", content=get_system_prompt()),
                    Message(role="user", content=assessment_context)
                ]
                assessment_history = [
                    {"role": "system", "content": "You are HealthGuide, a compassionate AI assistant for fever triage."},
                    {"role": "user", "content": assessment_context}
                ]
                
                response_message = llm_service.generate_response(assessment_messages, assessment_history)
                
                # Add triage summary information
                if triage_result.summary:
                    response_message = f"{response_message}\n\n📊 Assessment: {triage_result.summary}"
                
                if triage_result.recommended_next_steps:
                    response_message += f"\n\n📋 Recommended Next Steps:\n"
                    for i, step in enumerate(triage_result.recommended_next_steps[:3], 1):
                        response_message += f"{i}. {step}\n"
                
                conversation_complete = False  # Allow follow-up
            else:
                # Normal conversation flow
                response_message = llm_service.generate_response(messages, conversation_history)
                if triage_result.next_question and not has_structured_symptoms:
                    response_message += f"\n\n{triage_result.next_question}"
                conversation_complete = triage_result.next_question is None if not has_structured_symptoms else False

        updated_messages = [
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": response_message, "timestamp": datetime.now().isoformat()}
        ]
        
        # Ensure we have valid message dictionaries
        for msg in updated_messages:
            if not isinstance(msg, dict):
                msg = normalize_message_dict(msg) if hasattr(msg, '__dict__') else {"role": "user", "content": str(msg), "timestamp": datetime.now().isoformat()}
        save_conversation(
            db=db,
            session_id=request.session_id,
            messages=updated_messages,
            triage_level=triage_result.triage_level.value,
            summary=triage_result.summary,
            red_flag=triage_result.red_flag_symptom
        )

        return ConversationResponse(
            session_id=request.session_id,
            message=response_message,
            triage_result=triage_result,
            conversation_complete=conversation_complete
        )

    except Exception as e:
        import traceback
        print("❌ ERROR in /api/triage:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing triage request: {str(e)}")


# ------------------- SUMMARY ENDPOINT ------------------- #
@app.get("/api/summary/{session_id}", response_model=SummaryResponse)
async def get_summary(session_id: str, db: Session = Depends(get_db)):
    conversation = get_conversation(db, session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    triage_level = TriageLevel(conversation.triage_level) if conversation.triage_level else TriageLevel.FOLLOW_UP
    recommended_steps = [
        "Monitor your symptoms",
        "Stay hydrated",
        "Get plenty of rest",
        "Consult a healthcare provider if symptoms persist"
    ]
    return SummaryResponse(
        session_id=session_id,
        summary=conversation.summary or "Fever-related symptoms discussed",
        triage_level=triage_level,
        recommended_next_steps=recommended_steps,
        conversation_count=len(conversation.messages) if conversation.messages else 0
    )


# ------------------- PROVIDERS ENDPOINT ------------------- #
@app.post("/api/providers", response_model=List[Provider])
async def get_healthcare_providers(request: ProviderRequest):
    try:
        return get_providers(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching providers: {str(e)}")


# ------------------- SESSION & PROVIDER STATUS ------------------- #
@app.post("/api/session")
async def create_session():
    return {"session_id": str(uuid.uuid4()), "message": "New session created"}


@app.get("/api/llm-providers")
async def get_llm_providers():
    openai_available = bool(settings.openai_api_key and settings.openai_api_key not in ["", "your_key_here", "your-api-key"])
    gemini_available = bool(settings.gemini_api_key and settings.gemini_api_key not in ["", "your_key_here", "your-api-key"])
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI (GPT-4o Mini)", "available": openai_available},
            {"id": "gemini", "name": "Google Gemini 2.0 Flash", "available": gemini_available}
        ],
        "default": settings.llm_provider
    }


# ------------------- DEBUG API KEYS ------------------- #
@app.get("/api/debug/keys")
async def debug_api_keys():
    import os
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    return {
        "openai_configured": bool(settings.openai_api_key and settings.openai_api_key not in ["", "your_key_here", "your-api-key"]),
        "gemini_configured": bool(settings.gemini_api_key and settings.gemini_api_key not in ["", "your_key_here", "your-api-key"]),
        "env_file_exists": os.path.exists(env_file_path)
    }


# ------------------- TEMPERATURE ASSESSMENT ------------------- #
@app.post("/api/temperature/assess", response_model=TemperatureResponse)
async def assess_temperature(request: TemperatureRequest, db: Session = Depends(get_db)):
    """
    Smart temperature assessment endpoint - supports both numeric and descriptive input.
    """
    try:
        # Convert Fahrenheit to Celsius if provided
        temp_celsius = request.temperature_celsius
        if request.temperature_fahrenheit:
            temp_celsius = (request.temperature_fahrenheit - 32) * 5/9
        
        # Categorize temperature
        result = TemperatureHandler.categorize_temperature(
            temp_celsius=temp_celsius,
            descriptive=request.descriptive
        )
        
        # Save to database if we have a session_id and (a numeric value or descriptive input)
        if request.session_id and (temp_celsius or request.descriptive):
            try:
                temp_value = result.get("temperature_c", 37.0) if temp_celsius else 37.0
                save_temperature(
                    db=db,
                    session_id=request.session_id,
                    temperature=temp_value,
                    unit="C",
                    notes=f"Category: {result.get('category')}, Input: {request.descriptive or 'numeric'}"
                )
            except Exception as db_error:
                print(f"Warning: Could not save temperature to database: {db_error}")
                # Don't fail the request if database save fails
        
        return TemperatureResponse(
            category=result.get("category", "fever"),
            temperature_c=result.get("temperature_c"),
            temperature_f=result.get("temperature_f"),
            input_type=result.get("input_type", "unknown"),
            description=result.get("description", "Temperature assessed"),
            urgency=result.get("urgency", "moderate")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing temperature: {str(e)}")


@app.get("/api/temperature/questions")
async def get_temperature_questions():
    """Get temperature assessment questions and options"""
    return TemperatureHandler.get_temperature_questions()


@app.post("/api/temperature")
async def log_temperature(session_id: str, temperature: float, unit: str = "F", notes: str = None, db: Session = Depends(get_db)):
    try:
        temp_log = save_temperature(db, session_id, temperature, unit, notes)
        return {
            "id": temp_log.id,
            "session_id": temp_log.session_id,
            "temperature": temp_log.temperature,
            "unit": temp_log.unit,
            "recorded_at": temp_log.recorded_at.isoformat(),
            "notes": temp_log.notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging temperature: {str(e)}")


@app.get("/api/temperature/{session_id}")
async def get_temperature_history_endpoint(session_id: str, db: Session = Depends(get_db)):
    try:
        temp_logs = get_temperature_history(db, session_id)
        # Return empty list if no temperature logs found (not an error)
        return {
            "session_id": session_id,
            "temperatures": [
                {
                    "id": log.id,
                    "temperature": log.temperature,
                    "unit": log.unit,
                    "recorded_at": log.recorded_at.isoformat() if log.recorded_at else None,
                    "notes": log.notes
                } for log in temp_logs
            ] if temp_logs else []
        }
    except Exception as e:
        import traceback
        print(f"Error fetching temperature history: {traceback.format_exc()}")
        # Return empty list instead of error to prevent frontend issues
        return {
            "session_id": session_id,
            "temperatures": []
        }


# ------------------- NEW BUTTON ENDPOINTS ------------------- #
class ChatRequest(BaseModel):
    message: str
    provider: str | None = None


@app.post("/chat")
async def chat_with_llm(request: ChatRequest):
    """Emergency or quick chat endpoint"""
    try:
        llm_service = get_llm_service(provider=request.provider or settings.llm_provider)
        messages = [{"role": "user", "content": request.message}]
        response = llm_service.generate_response(messages, messages)
        return {"reply": response}
    except Exception as e:
        return {"reply": f"⚠️ Error: Could not process request. {str(e)}"}


class LocationRequest(BaseModel):
    lat: float
    lon: float


@app.post("/find_doctor")
async def find_doctor(request: LocationRequest):
    """Find nearby clinics using OpenStreetMap API"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q=clinic&limit=5&lat={request.lat}&lon={request.lon}"
        headers = {"User-Agent": "HealthGuide/1.0 (contact@example.com)"}
        response = requests.get(url, headers=headers, timeout=10)
        results = response.json()
        clinics = [
            {
                "name": r.get("display_name", "Unknown Clinic").split(",")[0],
                "address": r.get("display_name", "Address not available"),
                "lat": r.get("lat"),
                "lon": r.get("lon")
            } for r in results
        ]
        return {"clinics": clinics}
    except Exception as e:
        return {"clinics": [], "error": f"Unable to fetch nearby clinics: {str(e)}"}


@app.post("/triage")
async def triage_simple(request: ChatRequest):
    """Simplified triage route for Add to Triage button"""
    try:
        llm_service = get_llm_service(provider=request.provider or settings.llm_provider)
        messages = [{"role": "user", "content": f"The user reports: {request.message}"}]
        response = llm_service.generate_response(messages, messages)
        return {"reply": response}
    except Exception as e:
        return {"reply": f"⚠️ Error: Could not process triage request. {str(e)}"}


# ------------------- DISEASE DETECTION ------------------- #
@app.post("/api/disease/detect", response_model=DiseaseDetectionResponse)
async def detect_disease(request: DiseaseDetectionRequest):
    """
    Detect probable disease causes based on symptoms.
    """
    try:
        detector = DiseaseDetector()
        probable_causes = detector.detect_probable_causes(
            symptoms=request.symptoms,
            temperature_category=request.temperature_category,
            duration_days=request.duration_days,
            additional_context=request.additional_context or {}
        )
        
        # Get medication suggestions for top match
        medication_suggestions = None
        if probable_causes:
            top_disease = probable_causes[0]
            medication_suggestions = detector.get_medication_suggestions(
                disease_id=top_disease["disease_id"],
                age_group=request.additional_context.get("age_group", "adult") if request.additional_context else "adult",
                has_allergies=request.additional_context.get("has_allergies", False) if request.additional_context else False
            )
        
        return DiseaseDetectionResponse(
            probable_causes=[
                DiseaseMatch(**cause) for cause in probable_causes
            ],
            medication_suggestions=medication_suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting disease: {str(e)}")


# ------------------- GEOLOCATION PROVIDERS ------------------- #
@app.post("/api/providers/nearby", response_model=List[GeolocationProvider])
async def get_nearby_providers(request: GeolocationProviderRequest):
    """
    Find nearby healthcare providers using geolocation.
    """
    try:
        geo_service = GeolocationService()
        providers = await geo_service.find_nearby_healthcare_providers(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            provider_type=request.provider_type or "hospital",
            limit=request.limit
        )
        
        return [GeolocationProvider(**provider) for provider in providers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding nearby providers: {str(e)}")


@app.post("/api/providers/smart-find")
async def smart_find_doctor(
    request: GeolocationProviderRequest,
    db: Session = Depends(get_db)
):
    """
    Smart doctor finder that assesses if ambulance is needed and provides
    intelligent recommendations with hospital contacts.
    """
    try:
        geo_service = GeolocationService()
        llm_service = get_llm_service()
        
        # Extract optional fields from request
        session_id = request.session_id
        triage_level = request.triage_level
        symptoms = request.symptoms or []
        
        # Find nearby hospitals
        providers = await geo_service.find_nearby_healthcare_providers(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            provider_type="hospital",
            limit=5
        )
        
        # Get ambulance services info
        ambulance_info = await geo_service.find_ambulance_services(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km
        )
        
        # Assess if ambulance is needed using LLM
        assessment_context = f"""
        User location: {request.latitude}, {request.longitude}
        Triage level: {triage_level or 'UNKNOWN'}
        Symptoms: {', '.join(symptoms) if symptoms else 'Not provided'}
        
        Assess if the user needs:
        1. Immediate ambulance (life-threatening emergency)
        2. Urgent hospital visit (within 1-2 hours)
        3. Regular hospital/clinic visit (can wait)
        
        Respond in JSON format with:
        - needs_ambulance: boolean
        - urgency_level: "emergency" | "urgent" | "routine"
        - recommendation: string (brief advice)
        - estimated_response_time: string (for ambulance)
        """
        
        try:
            # Use OpenAI client directly if available
            if hasattr(llm_service, 'client') and llm_service.provider == "openai":
                assessment_response = llm_service.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a medical triage assistant. Assess if ambulance is needed based on symptoms and triage level. Respond ONLY in JSON format."},
                        {"role": "user", "content": assessment_context}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                assessment = json.loads(assessment_response.choices[0].message.content)
            else:
                # Fallback for Gemini or MockLLMService
                raise ValueError("Using fallback assessment")
        except Exception as e:
            print(f"LLM assessment error: {e}")
            # Fallback assessment based on triage level
            needs_ambulance = triage_level in ["EMERGENCY", "URGENT"]
            assessment = {
                "needs_ambulance": needs_ambulance,
                "urgency_level": "emergency" if needs_ambulance else "urgent" if triage_level == "URGENT" else "routine",
                "recommendation": "Seek immediate medical attention" if needs_ambulance else "Visit hospital as soon as possible" if triage_level == "URGENT" else "Schedule a hospital visit",
                "estimated_response_time": "5-15 minutes" if needs_ambulance else "N/A"
            }
        
        # Get conversation context if session_id provided
        conversation_summary = None
        if session_id:
            conversation = get_conversation(db, session_id)
            if conversation:
                conversation_summary = conversation.summary
        
        # Generate smart response using LLM
        smart_response_context = f"""
        User needs to find a doctor/hospital.
        Assessment: {assessment}
        Nearby hospitals found: {len(providers)}
        Emergency numbers: {ambulance_info.get('emergency_numbers', {})}
        Conversation summary: {conversation_summary or 'No prior conversation'}
        
        Provide a helpful, empathetic response that:
        1. Clearly states if ambulance is needed (if yes, emphasize calling immediately)
        2. Lists the nearest hospitals with phone numbers
        3. Provides emergency contact numbers
        4. Gives clear next steps
        5. Is reassuring but firm about urgency if needed
        
        Keep response concise and actionable.
        """
        
        try:
            smart_response = llm_service.generate_response(
                messages=[Message(role="user", content=smart_response_context)],
                conversation_history=[{"role": "user", "content": smart_response_context}]
            )
        except Exception as e:
            print(f"LLM smart response error: {e}")
            # Fallback response
            if assessment.get("needs_ambulance"):
                smart_response = f"""🚨 URGENT: Based on your symptoms, you may need immediate medical attention.

📞 Call Ambulance: {ambulance_info.get('emergency_numbers', {}).get('ambulance', '108')}
⏱️ Estimated response time: {assessment.get('estimated_response_time', '5-15 minutes')}

🏥 Nearest Hospitals:
"""
            else:
                smart_response = f"""📍 Based on your symptoms, here are the nearest hospitals:

🏥 Nearest Hospitals:
"""
            
            for i, provider in enumerate(providers[:3], 1):
                phone = provider.get("phone", "Phone not available")
                distance = provider.get("distance_km", 0)
                smart_response += f"\n{i}. {provider.get('name')} - {distance:.1f} km away\n   📞 {phone}\n"
        
        return {
            "assessment": assessment,
            "providers": [GeolocationProvider(**provider) for provider in providers],
            "ambulance_info": ambulance_info,
            "smart_response": smart_response,
            "emergency_numbers": ambulance_info.get("emergency_numbers", {})
        }
    except Exception as e:
        import traceback
        print(f"Error in smart_find_doctor: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error finding providers: {str(e)}")


# ------------------- MEDICATION REMINDERS ------------------- #
@app.post("/api/medication/reminder", response_model=MedicationReminderResponse)
async def create_medication_reminder(request: MedicationReminderRequest, db: Session = Depends(get_db)):
    """
    Create a medication reminder.
    """
    try:
        reminder = MedicationService.create_reminder(
            db=db,
            session_id=request.session_id,
            medication_name=request.medication_name,
            dosage=request.dosage,
            frequency=request.frequency,
            duration_days=request.duration_days,
            notes=request.notes
        )
        
        schedule = MedicationService.get_reminder_schedule(reminder)
        frequency_info = MedicationService.FREQUENCY_OPTIONS.get(request.frequency, {})
        
        return MedicationReminderResponse(
            id=reminder.id,
            medication_name=reminder.medication_name,
            dosage=reminder.dosage,
            frequency=reminder.frequency,
            frequency_label=frequency_info.get("label", reminder.frequency),
            duration_days=reminder.duration_days,
            start_date=reminder.start_date.isoformat(),
            end_date=reminder.end_date.isoformat() if reminder.end_date else None,
            notes=reminder.notes,
            schedule=schedule,
            next_dose=schedule[0] if schedule else None,
            total_doses=len(schedule)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating medication reminder: {str(e)}")


@app.get("/api/medication/reminders/{session_id}")
async def get_medication_reminders(session_id: str, db: Session = Depends(get_db)):
    """
    Get all active medication reminders for a session.
    """
    try:
        reminders = MedicationService.get_active_reminders(db, session_id)
        return {"reminders": reminders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching medication reminders: {str(e)}")


@app.delete("/api/medication/reminder/{reminder_id}")
async def stop_medication_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """
    Stop/deactivate a medication reminder.
    """
    try:
        success = MedicationService.stop_reminder(db, reminder_id)
        if success:
            return {"message": "Reminder stopped successfully"}
        else:
            raise HTTPException(status_code=404, detail="Reminder not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping reminder: {str(e)}")


@app.get("/api/medication/frequency-options")
async def get_frequency_options():
    """
    Get available medication frequency options.
    """
    return MedicationService.get_frequency_options()


# ------------------- ANALYTICS ------------------- #
@app.get("/api/analytics/dashboard", response_model=AnalyticsResponse)
async def get_analytics_dashboard(days: int = 7, region: Optional[str] = None, country: str = "India", db: Session = Depends(get_db)):
    """
    Get analytics dashboard data for public health monitoring.
    """
    try:
        summary_stats = AnalyticsService.get_summary_stats(db, days=days)
        geographic_trends = AnalyticsService.get_geographic_trends(db, days=days, country=country)
        disease_distribution = AnalyticsService.get_disease_distribution(db, days=days, region=region)
        time_series_data = AnalyticsService.get_time_series_data(db, days=days)
        potential_outbreaks = AnalyticsService.detect_potential_outbreaks(db)
        
        return AnalyticsResponse(
            summary_stats=summary_stats,
            geographic_trends=geographic_trends,
            disease_distribution=disease_distribution,
            time_series_data=time_series_data,
            potential_outbreaks=potential_outbreaks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")


@app.post("/api/analytics/log-case")
async def log_fever_case(
    session_id: str,
    location_data: dict,
    symptom_data: dict,
    triage_result: dict,
    db: Session = Depends(get_db)
):
    """
    Log anonymized fever case for trend analysis.
    """
    try:
        AnalyticsService.log_fever_case(
            db=db,
            session_id=session_id,
            location_data=location_data,
            symptom_data=symptom_data,
            triage_result=triage_result
        )
        return {"message": "Case logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging case: {str(e)}")


# ------------------- APP RUNNER ------------------- #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
