import io

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Language codes for gTTS
TTS_LANG_CODES = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Bengali": "bn",
    "Marathi": "mr"
}

def text_to_speech(text: str, language: str = "English") -> bytes:
    """Convert text to speech"""
    if not GTTS_AVAILABLE:
        return None
    
    try:
        lang_code = TTS_LANG_CODES.get(language, "en")
        tts = gTTS(text=text, lang=lang_code, slow=False)
        
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue()
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

# Pre-defined prompts
TTS_PROMPTS = {
    "English": {
        "welcome": "Welcome to MediKiosk. Please select your preferred language.",
        "consent": "Please provide your consent to continue.",
        "chief_complaint": "Please tell us what is troubling you today.",
        "thank_you": "Thank you. Your information has been recorded. Please proceed to the waiting area."
    },
    "Hindi": {
        "welcome": "मेडीकियोस्क में आपका स्वागत है। कृपया अपनी पसंदीदा भाषा चुनें।",
        "consent": "कृपया आगे बढ़ने के लिए अपनी सहमति दें।",
        "chief_complaint": "कृपया बताएं कि आज आपको क्या परेशानी है।",
        "thank_you": "धन्यवाद। आपकी जानकारी दर्ज कर ली गई है। कृपया प्रतीक्षा क्षेत्र में जाएं।"
    }
}