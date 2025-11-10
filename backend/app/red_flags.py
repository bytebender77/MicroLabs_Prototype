"""Red flag symptom detection"""
from typing import Optional, Dict, List


# Red flag symptoms that truly require emergency care
RED_FLAG_SYMPTOMS: Dict[str, List[str]] = {
    "severe difficulty breathing": [
        "severe difficulty breathing", "can't breathe", "cannot breathe",
        "trouble breathing", "difficulty breathing", "shortness of breath",
        "struggling to breathe", "hard to breathe", "breathing problems",
        "gasping for air", "unable to breathe"
    ],
    "chest pain or pressure": [
        "chest pain", "chest pressure", "chest tightness", "chest discomfort",
        "pressure in chest", "pain in chest", "tight chest", "heart pain"
    ],
    "confusion or inability to stay awake": [
        "confusion", "confused", "can't stay awake", "cannot stay awake",
        "unable to stay awake", "drowsy", "unconscious", "passed out",
        "disoriented", "mental confusion", "losing consciousness"
    ],
    "bluish lips or face": [
        "blue lips", "bluish lips", "blue face", "bluish face", "cyanosis",
        "lips turning blue", "face turning blue", "blue skin", "purple lips"
    ],
    "severe dehydration": [
        "no urine", "no urination", "haven't urinated", "no urine for",
        "sunken eyes", "severe dehydration", "severely dehydrated",
        "8 hours", "8+ hours", "no urine for 8", "not urinated for 8 hours"
    ],
    "seizure": [
        "seizure", "seizures", "convulsion", "convulsions", "fitting",
        "having a seizure", "had a seizure", "seizing"
    ],
    "severe headache or stiff neck with light sensitivity": [
        "severe headache", "stiff neck with light sensitivity", "light sensitivity",
        "photophobia", "sensitive to light", "neck stiffness", "stiff neck and light",
        "headache with stiff neck"
    ],
    "rash that does not fade when pressed": [
        "rash that does not fade", "rash doesn't fade", "non-blanching rash",
        "petechiae", "rash that won't fade", "rash that doesn't fade under pressure",
        "rash that doesn't fade when pressed", "non-blanching"
    ]
}


def check_red_flags(user_input: str, emergency_detected: bool = False) -> Optional[str]:
    """
    Detect red flag symptoms ONLY when emergency_detected=True (from frontend).
    This prevents false emergency triggers for mild symptoms like 'fever' or 'itching'.
    """
    if not user_input or not emergency_detected:
        return None

    user_input_lower = user_input.lower()

    for symptom, keywords in RED_FLAG_SYMPTOMS.items():
        for keyword in keywords:
            if keyword.lower() in user_input_lower:
                return symptom

    return None


def get_red_flag_response(symptom: str) -> str:
    """Return a clear emergency response for detected red flag symptom"""
    return (
        f"⚠️ **URGENT:** I've detected a potential red flag symptom: **{symptom}**.\n\n"
        "🚨 **This may be serious. Please call emergency services or go to the nearest emergency department now.**\n\n"
        "I am not a doctor, but I recommend:\n"
        "• Call your local emergency number (e.g., 108, 112, 911)\n"
        "• Go to the nearest emergency room\n"
        "• Do not delay seeking medical attention\n"
    )
