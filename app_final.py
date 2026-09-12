import streamlit as st
import json
import os
import base64
from datetime import datetime
from PIL import Image
import pytesseract
import io
import re

# Import our modules
from database import (
    save_patient, save_consultation, get_all_consultations,
    get_consultation_by_token, get_stats
)
from utils_voice import get_translation, get_voice_lang, TRANSLATIONS
from utils_pdf import extract_text_from_pdf
from utils_qr import generate_abha_qr

# Optional imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

# Set Tesseract path
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI
if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    openai_client = None

# Page config
st.set_page_config(
    page_title="MediKiosk - AI Clinical History",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
def load_css():
    try:
        with open("styles.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

# Initialize session state
defaults = {
    'step': 1,
    'language': 'English',
    'patient_data': {},
    'documents': [],
    'ai_analysis': {},
    'fhir_bundle': None,
    'voice_transcript': '',
    'voice_lang': 'en-IN',
    'view': 'patient',  # 'patient' or 'doctor'
    'token_number': None,
    'patient_id': None
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Translation helper
def t(key):
    return get_translation(st.session_state.language, key)

# ============================================
# AI FUNCTIONS
# ============================================
def generate_ai_summary(patient_data):
    """Generate AI summary"""
    if not openai_client:
        return generate_rule_based_summary(patient_data)
    
    try:
        prompt = f"""Generate a clinical summary as JSON from this patient data:
        {json.dumps(patient_data, indent=2)}
        
        Return JSON with keys: chief_complaint, hpi, findings, risk_assessment, recommendations"""
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical AI assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        text = response.choices[0].message.content
        # Clean JSON
        text = text.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(text)
        except:
            return generate_rule_based_summary(patient_data)
    except Exception as e:
        return generate_rule_based_summary(patient_data)

def generate_rule_based_summary(data):
    """Fallback summary"""
    chief = data.get('chief_complaint', '')
    duration = data.get('duration', '')
    symptoms = data.get('symptoms', [])
    
    hpi = f"Patient presents with {chief}"
    if duration:
        hpi += f" for {duration.lower()}"
    if symptoms:
        hpi += f". Associated symptoms: {', '.join(symptoms)}"
    hpi += "."
    
    # Risk assessment
    chief_lower = chief.lower()
    symptoms_lower = [s.lower() for s in symptoms]
    risk = "Standard - Routine evaluation"
    
    if 'chest pain' in chief_lower and 'shortness of breath' in symptoms_lower:
        risk = "HIGH - Possible cardiac emergency. Immediate ECG required."
    elif 'chest pain' in chief_lower:
        risk = "MODERATE - Cardiac evaluation recommended"
    elif 'breathing' in chief_lower:
        risk = "MODERATE - Respiratory assessment needed"
    
    return {
        "chief_complaint": chief,
        "hpi": hpi,
        "findings": f"Duration: {duration}. Symptoms reported: {len(symptoms)}",
        "risk_assessment": risk,
        "recommendations": "Complete physical examination and relevant investigations."
    }

def extract_entities(text):
    """Extract medical entities"""
    if not openai_client or not text:
        return {"medications": [], "diagnoses": [], "lab_values": []}
    
    try:
        prompt = f"""Extract medical entities from this text and return JSON:
        
        Text: {text[:1000]}
        
        Return: {{"medications": [], "diagnoses": [], "lab_values": []}}"""
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        
        text_result = response.choices[0].message.content
        text_result = text_result.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(text_result)
        except:
            return {"medications": [], "diagnoses": [], "lab_values": []}
    except:
        return {"medications": [], "diagnoses": [], "lab_values": []}

def detect_red_flags(data):
    """Detect red flags"""
    chief = data.get('chief_complaint', '').lower()
    symptoms = [s.lower() for s in data.get('symptoms', [])]
    
    flags = []
    
    if 'chest pain' in chief and 'shortness of breath' in symptoms:
        flags.append({
            "level": "CRITICAL",
            "message": "🚨 Chest pain with dyspnea - Possible MI/PE",
            "action": "Immediate ECG, troponin, O2 saturation"
        })
    elif 'chest pain' in chief and 'sweating' in symptoms:
        flags.append({
            "level": "CRITICAL",
            "message": "🚨 Chest pain with diaphoresis - Possible ACS",
            "action": "Immediate ECG, cardiac monitoring"
        })
    elif 'chest pain' in chief:
        flags.append({
            "level": "HIGH",
            "message": "⚠️ Chest pain reported",
            "action": "ECG recommended within 10 minutes"
        })
    
    if 'breathing' in chief or 'breath' in chief:
        flags.append({
            "level": "HIGH",
            "message": "⚠️ Breathing difficulty",
            "action": "Check SpO2, respiratory rate"
        })
    
    if 'headache' in chief and 'dizziness' in symptoms:
        flags.append({
            "level": "MODERATE",
            "message": "⚠️ Headache with dizziness",
            "action": "Neurological exam, BP check"
        })
    
    return flags

def generate_fhir_bundle(data, ai_summary):
    """Generate FHIR bundle"""
    return {
        "resourceType": "Bundle",
        "type": "document",
        "timestamp": datetime.now().isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": "Composition",
                    "status": "final",
                    "title": "MediKiosk Clinical Summary",
                    "date": datetime.now().isoformat(),
                    "section": [
                        {"title": "Chief Complaint", "text": {"div": data.get('chief_complaint', '')}},
                        {"title": "HPI", "text": {"div": ai_summary.get('hpi', '')}},
                        {"title": "Allergies", "text": {"div": data.get('allergies', 'None')}}
                    ]
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {"text": data.get('chief_complaint', '')},
                    "clinicalStatus": {"coding": [{"code": "active"}]}
                }
            }
        ]
    }

# ============================================
# VOICE FUNCTION
# ============================================
def record_voice():
    if not SPEECH_AVAILABLE:
        return None, "Speech recognition not available"
    
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
        
        try:
            text = r.recognize_google(audio, language=st.session_state.voice_lang)
            return text, None
        except sr.UnknownValueError:
            return None, "Could not understand. Try again."
        except sr.RequestError as e:
            return None, f"Service error: {e}"
    except Exception as e:
        return None, f"Error: {e}"

# ============================================
# OCR FUNCTION
# ============================================
def extract_ocr(image):
    try:
        return pytesseract.image_to_string(image)
    except Exception as e:
        return f"Error: {e}"

# ============================================
# VIEW SELECTOR (Patient vs Doctor)
# ============================================
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("# 🏥 MediKiosk")
with col2:
    if st.button("👤 Patient Mode", use_container_width=True, 
                 type="primary" if st.session_state.view == "patient" else "secondary"):
        st.session_state.view = "patient"
        st.session_state.step = 1
        st.rerun()
with col3:
    if st.button("👨‍⚕️ Doctor Mode", use_container_width=True,
                 type="primary" if st.session_state.view == "doctor" else "secondary"):
        st.session_state.view = "doctor"
        st.rerun()

st.markdown("---")

# ============================================
# DOCTOR VIEW
# ============================================
if st.session_state.view == "doctor":
    st.markdown("## 👨‍⚕️ Doctor Dashboard")
    
    # Stats
    stats = get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Patients", stats['total_patients'])
    with col2:
        st.metric("Today's Consultations", stats['today_consultations'])
    with col3:
        st.metric("High Risk Cases", stats['high_risk_cases'], delta_color="inverse")
    with col4:
        st.metric("Documents Processed", stats['total_documents'])
    
    st.markdown("---")
    
    # Recent consultations
    st.markdown("### 📋 Recent Consultations")
    consultations = get_all_consultations(20)
    
    if consultations:
        for c in consultations:
            risk = c.get('risk_assessment', '')
            is_high_risk = 'HIGH' in risk or 'CRITICAL' in risk
            
            with st.expander(f"🎫 {c['token_number']} - {c.get('name', 'Unknown')} ({c.get('age', '?')}y)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Chief Complaint:** {c.get('chief_complaint', 'N/A')}")
                    st.write(f"**Duration:** {c.get('duration', 'N/A')}")
                    st.write(f"**Allergies:** {c.get('allergies', 'None')}")
                    st.write(f"**Time:** {c.get('created_at', 'N/A')}")
                
                with col2:
                    if is_high_risk:
                        st.error(f"⚠️ {risk}")
                    else:
                        st.success(f"✅ {risk}")
                    
                    st.write(f"**Medications:** {c.get('medications', 'None')}")
                
                # AI Summary
                try:
                    ai_summary = json.loads(c.get('ai_summary', '{}'))
                    if ai_summary.get('hpi'):
                        st.markdown("**AI Summary:**")
                        st.write(ai_summary['hpi'])
                except:
                    pass
    else:
        st.info("No consultations yet. Complete a patient session to see data here.")

# ============================================
# PATIENT VIEW
# ============================================
else:
    # Progress indicator
    steps = ["Consent", "Complaint", "History", "Documents", "Summary"]
    current = st.session_state.step
    
    progress_html = '<div class="progress-container">'
    for i, step_name in enumerate(steps, 1):
        if i < current:
            cls = "completed"
            icon = "✓"
        elif i == current:
            cls = "active"
            icon = str(i)
        else:
            cls = ""
            icon = str(i)
        
        progress_html += f'''
            <div class="progress-step {cls}">
                <div class="step-circle">{icon}</div>
                <div class="step-label">{step_name}</div>
            </div>
        '''
    progress_html += '</div>'
    st.markdown(progress_html, unsafe_allow_html=True)
    
    # ============ STEP 1: CONSENT ============
    if st.session_state.step == 1:
        st.markdown('<div class="kiosk-header"><h1>🏥 Welcome to MediKiosk</h1><p>Your health, your voice</p></div>', unsafe_allow_html=True)
        
        # Language selection
        st.markdown("### 🌐 Select Language / भाषा चुनें")
        
        languages = ["English", "Hindi", "Tamil", "Telugu"]
        cols = st.columns(len(languages))
        
        for i, lang in enumerate(languages):
            with cols[i]:
                flags = {"English": "🇬🇧", "Hindi": "🇮🇳", "Tamil": "🇮🇳", "Telugu": "🇮🇳"}
                btn_type = "primary" if st.session_state.language == lang else "secondary"
                if st.button(f"{flags[lang]} {lang}", use_container_width=True, type=btn_type):
                    st.session_state.language = lang
                    st.session_state.patient_data['language'] = lang
                    st.session_state.voice_lang = get_voice_lang(lang)
                    st.rerun()
        
        st.markdown("---")
        
        # Patient info (optional)
        st.markdown("### 👤 Patient Information (Optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name / नाम", key="p_name")
            age = st.number_input("Age / उम्र", min_value=0, max_value=120, value=30, key="p_age")
        with col2:
            gender = st.selectbox("Gender / लिंग", ["Male", "Female", "Other"], key="p_gender")
            phone = st.text_input("Phone / फ़ोन", key="p_phone")
        
        abha_id = st.text_input("ABHA ID (if available)", placeholder="12-3456-7890-1234", key="p_abha")
        
        if abha_id:
            try:
                qr_bytes = generate_abha_qr(abha_id, name)
                st.image(qr_bytes, caption="Your ABHA QR Code", width=150)
            except:
                pass
        
        # Store in session
        st.session_state.patient_data.update({
            'name': name,
            'age': age,
            'gender': gender,
            'phone': phone,
            'abha_id': abha_id if abha_id else f"GUEST{datetime.now().strftime('%Y%m%d%H%M%S')}"
        })
        
        st.markdown("---")
        
        # Consent
        st.markdown("### 📋 Consent")
        
        consent_text = {
            "English": "I consent to share my health information for medical purposes. My data will be stored securely.",
            "Hindi": "मैं चिकित्सा उद्देश्यों के लिए अपनी स्वास्थ्य जानकारी साझा करने के लिए सहमति देता/देती हूं।",
            "Tamil": "மருத்துவ நோக்கங்களுக்காக எனது சுகாதார தகவல்களைப் பகிர எனது ஒப்புதலை அளிக்கிறேன்.",
            "Telugu": "వైద్య ప్రయోజనాల కోసం నా ఆరోగ్య సమాచారాన్ని పంచుకోవడానికి నేను సమ్మతిస్తున్నాను."
        }
        
        st.info(consent_text.get(st.session_state.language, consent_text["English"]))
        
        consent = st.checkbox(t("consent"), key="consent_check")
        
        if consent:
            if st.button(f"🚀 {t('start')}", type="primary", use_container_width=True):
                st.session_state.patient_data['consent_given'] = True
                st.session_state.patient_data['consent_time'] = datetime.now().isoformat()
                st.session_state.step = 2
                st.rerun()
        else:
            st.warning("⚠️ Please provide consent to continue / कृपया जारी रखने के लिए सहमति दें")
    
    # ============ STEP 2: CHIEF COMPLAINT ============
    elif st.session_state.step == 2:
        st.markdown(f"## 🎯 {t('chief_complaint')}")
        st.markdown("---")
        
        # Voice input
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎤 Speak")
            if st.button("🎤 " + t('speak'), type="primary", use_container_width=True):
                text, error = record_voice()
                if error:
                    st.error(error)
                elif text:
                    st.session_state.voice_transcript = text
                    st.session_state.patient_data['chief_complaint'] = text
                    st.session_state.step = 3
                    st.rerun()
        
        with col2:
            st.markdown("### ⌨️ Type")
            typed = st.text_area(t('type_here'), height=100, key="complaint_text")
            if typed and st.button(t('submit'), use_container_width=True):
                st.session_state.patient_data['chief_complaint'] = typed
                st.session_state.step = 3
                st.rerun()
        
        st.markdown("---")
        
        # Quick options
        st.markdown("### ⚡ Quick Selection")
        
        complaints = [
            ("💔", "Chest Pain"),
            ("🤕", "Headache"),
            ("🤒", "Fever"),
            ("😤", "Breathing Difficulty"),
            ("🤢", "Nausea/Vomiting"),
            ("🦴", "Joint Pain"),
            ("😣", "Abdominal Pain"),
            ("😴", "Fatigue"),
            ("🩸", "Bleeding"),
            ("🦷", "Tooth Pain"),
            ("👁️", "Eye Problem"),
            ("👂", "Ear Problem")
        ]
        
        cols = st.columns(4)
        for i, (icon, complaint) in enumerate(complaints):
            with cols[i % 4]:
                if st.button(f"{icon} {complaint}", use_container_width=True, key=f"c_{i}"):
                    st.session_state.patient_data['chief_complaint'] = complaint
                    st.session_state.step = 3
                    st.rerun()
    
    # ============ STEP 3: HISTORY ============
    elif st.session_state.step == 3:
        chief = st.session_state.patient_data.get('chief_complaint', '')
        st.markdown(f"## 📝 History: {chief}")
        st.markdown("---")
        
        # Duration
        st.markdown("### ⏰ Duration")
        duration = st.radio(
            "How long?",
            ["Today", "1-2 days", "3-5 days", "1-2 weeks", "More than a month"],
            horizontal=True,
            key="dur"
        )
        st.session_state.patient_data['duration'] = duration
        
        # Severity
        if any(w in chief.lower() for w in ['pain', 'ache', 'headache']):
            st.markdown("### 📊 Severity")
            sev = st.slider("Pain level (1-10)", 1, 10, 5, key="sev")
            st.session_state.patient_data['severity'] = sev
            
            if sev <= 3:
                st.success("🟢 Mild")
            elif sev <= 7:
                st.warning("🟡 Moderate")
            else:
                st.error("🔴 Severe")
        
        st.markdown("---")
        
        # Symptoms
        st.markdown("### 🔍 Symptoms")
        symptoms = st.multiselect(
            "Select all that apply:",
            ["Nausea", "Dizziness", "Sweating", "Shortness of breath",
             "Cough", "Body ache", "Fatigue", "Loss of appetite",
             "Palpitations", "Anxiety", "None"],
            key="sym"
        )
        st.session_state.patient_data['symptoms'] = symptoms
        
        st.markdown("---")
        
        # Past history
        st.markdown("### 📋 Past History")
        past = st.multiselect(
            "Existing conditions:",
            ["Diabetes", "Hypertension", "Heart Disease", "Asthma",
             "Thyroid", "Kidney Disease", "Liver Disease", "None"],
            key="past"
        )
        st.session_state.patient_data['past_history'] = past
        
        st.markdown("---")
        
        # Medications
        st.markdown("### 💊 Medications")
        meds = st.text_input("Current medications (comma separated):", key="meds")
        st.session_state.patient_data['medications'] = meds
        
        st.markdown("---")
        
        # Allergies
        st.markdown("### ⚠️ Allergies")
        allergy = st.radio(
            "Drug allergies:",
            ["None", "Penicillin", "Sulfa", "Aspirin", "Other"],
            horizontal=True,
            key="alg"
        )
        st.session_state.patient_data['allergies'] = allergy
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("← " + t('back'), use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        with col2:
            if st.button(t('next') + " →", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
    
    # ============ STEP 4: DOCUMENTS ============
    elif st.session_state.step == 4:
        st.markdown("## 📄 Upload Documents")
        st.markdown("---")
        
        uploaded = st.file_uploader(
            "Upload prescriptions, lab reports, or scans",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            accept_multiple_files=True
        )
        
        if uploaded:
            for file in uploaded:
                if file.name not in [d['filename'] for d in st.session_state.documents]:
                    with st.spinner(f"Processing {file.name}..."):
                        
                        if file.type == 'application/pdf':
                            text = extract_text_from_pdf(file)
                            entities = extract_entities(text[:1000])
                            
                            st.session_state.documents.append({
                                'filename': file.name,
                                'type': 'pdf',
                                'extracted_text': text[:500],
                                'entities': entities
                            })
                            st.success(f"✅ {file.name} processed")
                        
                        elif file.type in ['image/jpeg', 'image/png', 'image/jpg']:
                            img = Image.open(file)
                            st.image(img, caption=file.name, width=250)
                            
                            text = extract_ocr(img)
                            entities = extract_entities(text[:1000])
                            
                            st.session_state.documents.append({
                                'filename': file.name,
                                'type': 'image',
                                'extracted_text': text[:500],
                                'entities': entities
                            })
                            
                            with st.expander(f"📄 {file.name} Analysis"):
                                st.text(text[:300])
                                if entities.get('medications'):
                                    st.markdown("**Medications:**")
                                    for m in entities['medications'][:5]:
                                        st.write(f"• {m}")
                            
                            st.success(f"✅ {file.name} processed")
        
        if st.session_state.documents:
            st.markdown("---")
            st.markdown(f"### 📚 {len(st.session_state.documents)} Document(s)")
            for d in st.session_state.documents:
                st.write(f"• {d['filename']}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← " + t('back'), use_container_width=True):
                st.session_state.step = 3
                st.rerun()
        with col2:
            if st.button("Generate Summary →", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is analyzing..."):
                    # Generate AI summary
                    ai_summary = generate_ai_summary(st.session_state.patient_data)
                    st.session_state.ai_analysis['summary'] = ai_summary
                    
                    # Red flags
                    st.session_state.ai_analysis['red_flags'] = detect_red_flags(st.session_state.patient_data)
                    
                    # FHIR
                    st.session_state.fhir_bundle = generate_fhir_bundle(
                        st.session_state.patient_data, ai_summary
                    )
                    
                    # Save to database
                    patient_id = save_patient(st.session_state.patient_data)
                    if patient_id:
                        st.session_state.patient_id = patient_id
                        
                        save_data = {
                            **st.session_state.patient_data,
                            'ai_summary': ai_summary,
                            'risk_assessment': ai_summary.get('risk_assessment', ''),
                            'documents': st.session_state.documents,
                            'fhir_bundle': st.session_state.fhir_bundle
                        }
                        token = save_consultation(patient_id, save_data)
                        st.session_state.token_number = token
                
                st.session_state.step = 5
                st.rerun()
    
    # ============ STEP 5: SUMMARY ============
    elif st.session_state.step == 5:
        st.balloons()
        st.markdown('<div class="kiosk-header"><h1>✅ Thank You!</h1><p>Your information has been recorded</p></div>', unsafe_allow_html=True)
        
        # Token number
        if st.session_state.token_number:
            st.markdown(f'''
                <div class="token-display">
                    <p style="margin:0; font-size:1.2em;">Your Token Number</p>
                    <div class="token-number">{st.session_state.token_number}</div>
                    <p style="margin:0; opacity:0.9;">Please proceed to the waiting area</p>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown("---")
        
        data = st.session_state.patient_data
        ai_summary = st.session_state.ai_analysis.get('summary', {})
        red_flags = st.session_state.ai_analysis.get('red_flags', [])
        
        # Red flags FIRST
        if red_flags:
            for flag in red_flags:
                if flag['level'] == 'CRITICAL':
                    st.error(f"### {flag['message']}\n**Action:** {flag['action']}")
                elif flag['level'] == 'HIGH':
                    st.warning(f"### {flag['message']}\n**Action:** {flag['action']}")
                else:
                    st.info(f"### {flag['message']}\n**Action:** {flag['action']}")
        
        # Summary
        st.markdown("## 📋 Clinical Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Chief Complaint")
            st.info(data.get('chief_complaint', ''))
            
            st.markdown("### ⏰ Duration")
            st.write(data.get('duration', ''))
            
            st.markdown("### 📊 Severity")
            if 'severity' in data:
                st.write(f"{data['severity']}/10")
                st.progress(data['severity'] / 10)
            
            st.markdown("### 🔍 Symptoms")
            for s in data.get('symptoms', []):
                st.write(f"• {s}")
        
        with col2:
            st.markdown("### 📋 Past History")
            for p in data.get('past_history', []):
                st.write(f"• {p}")
            
            st.markdown("### 💊 Medications")
            st.write(data.get('medications', 'None') or 'None')
            
            st.markdown("### ⚠️ Allergies")
            st.write(data.get('allergies', 'None'))
        
        st.markdown("---")
        
        # AI Summary
        if ai_summary.get('hpi'):
            st.markdown("### 🤖 AI-Generated HPI")
            st.write(ai_summary['hpi'])
        
        if ai_summary.get('recommendations'):
            st.markdown("### 💡 Recommendations")
            st.write(ai_summary['recommendations'])
        
        # Documents
        if st.session_state.documents:
            st.markdown("### 📚 Uploaded Documents")
            for d in st.session_state.documents:
                st.write(f"• {d['filename']}")
        
        st.markdown("---")
        
        # Actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🖨️ Print", use_container_width=True):
                st.info("Print feature - connect to printer")
        
        with col2:
            full_data = {
                'patient_info': data,
                'ai_summary': ai_summary,
                'documents': st.session_state.documents,
                'fhir_bundle': st.session_state.fhir_bundle,
                'token': st.session_state.token_number,
                'generated_at': datetime.now().isoformat()
            }
            json_str = json.dumps(full_data, indent=2, default=str)
            st.download_button(
                label="📄 Download",
                data=json_str,
                file_name=f"{st.session_state.token_number or 'summary'}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            if st.button("🔄 New Patient", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # FHIR bundle
        with st.expander("🏥 FHIR Bundle (ABDM)"):
            st.json(st.session_state.fhir_bundle or {})

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p><strong>MediKiosk v1.0</strong> - AI-Powered Clinical History Platform</p>
        <p>Voice Input | Document OCR | AI Summarization | FHIR/ABDM | Multi-language</p>
        <p>Built for Hackathon Demo</p>
    </div>
    """,
    unsafe_allow_html=True
)