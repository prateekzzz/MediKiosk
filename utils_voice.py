import streamlit as st

# Language codes for voice recognition
VOICE_LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Bengali": "bn-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Punjabi": "pa-IN"
}

# Multilingual UI strings
TRANSLATIONS = {
    "English": {
        "welcome": "Welcome",
        "consent": "I give my consent to proceed",
        "start": "Start",
        "chief_complaint": "What is your main problem?",
        "speak": "Click to Speak",
        "type_here": "Or type here",
        "next": "Next",
        "back": "Back",
        "submit": "Submit",
        "thank_you": "Thank you",
        "summary": "Your Health Summary"
    },
    "Hindi": {
        "welcome": "स्वागत है",
        "consent": "मैं आगे बढ़ने के लिए सहमति देता/देती हूं",
        "start": "शुरू करें",
        "chief_complaint": "आपकी मुख्य समस्या क्या है?",
        "speak": "बोलने के लिए क्लिक करें",
        "type_here": "या यहाँ लिखें",
        "next": "आगे",
        "back": "पीछे",
        "submit": "जमा करें",
        "thank_you": "धन्यवाद",
        "summary": "आपका स्वास्थ्य सारांश"
    },
    "Tamil": {
        "welcome": "வரவேற்பு",
        "consent": "தொடர எனது ஒப்புதலை அளிக்கிறேன்",
        "start": "தொடங்கு",
        "chief_complaint": "உங்கள் முக்கிய பிரச்சினை என்ன?",
        "speak": "பேச கிளிக் செய்யவும்",
        "type_here": "அல்லது இங்கே தட்டச்சு செய்யவும்",
        "next": "அடுத்து",
        "back": "பின்னால்",
        "submit": "சமர்ப்பிக்கவும்",
        "thank_you": "நன்றி",
        "summary": "உங்கள் சுகாதார சுருக்கம்"
    },
    "Telugu": {
        "welcome": "స్వాగతం",
        "consent": "కొనసాగడానికి నా సమ్మతి ఇస్తున్నాను",
        "start": "ప్రారంభించండి",
        "chief_complaint": "మీ ప్రధాన సమస్య ఏమిటి?",
        "speak": "మాట్లాడటానికి క్లిక్ చేయండి",
        "type_here": "లేదా ఇక్కడ టైప్ చేయండి",
        "next": "తదుపరి",
        "back": "వెనుక",
        "submit": "సమర్పించండి",
        "thank_you": "ధన్యవాదాలు",
        "summary": "మీ ఆరోగ్య సారాంశం"
    }
}

def get_translation(language: str, key: str) -> str:
    """Get translated string"""
    return TRANSLATIONS.get(language, TRANSLATIONS["English"]).get(key, key)

def get_voice_lang(language: str) -> str:
    """Get voice language code"""
    return VOICE_LANGUAGES.get(language, "en-IN")