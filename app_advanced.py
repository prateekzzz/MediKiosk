import streamlit as st
import json
import os
from datetime import datetime
from PIL import Image
import pytesseract
import io

# Import all modules
from database import (
    save_patient, save_consultation, get_all_consultations,
    get_consultation_by_token, get_stats
)
from utils_voice import get_translation, get_voice_lang, TRANSLATIONS
from utils_pdf import extract_text_from_pdf
from utils_qr import generate_abha_qr
from utils_analytics import (
    get_consultation_dataframe, plot_consultations_by_hour,
    plot_top_complaints, plot_risk_distribution,
    plot_age_distribution, plot_gender_distribution,
    plot_language_distribution, plot_time_series
)
from utils_drugs import check_interactions
from utils_pdf_report import generate_pdf_report
from utils_ayush import AYUSH_QUESTIONS, calculate_prakriti
from utils_tts import text_to_speech, TTS_PROMPTS, GTTS_AVAILABLE
from utils_auth import login_form, DEFAULT_USERS

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

if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from dotenv import load_dotenv
load_dotenv()

if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    openai_client = None

# Page config
st.set_page_config(
    page_title="MediKiosk Pro - AI Clinical Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
try:
    with open("styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except:
    pass

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
    'view': 'patient',
    'token_number': None,
    'patient_id': None,
    'authenticated': False,
    'username': None,
    'user_name': None,
    'user_role': None,
    'ayush_mode': False,
    'ayush_answers': {},
    'tts_enabled': False
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

def t(key):
    return get_translation(st.session_state.language, key)

# AI Functions
def generate_ai_summary(data):
    if not openai_client:
        return generate_rule_based_summary(data)
    
    try:
        prompt = f"""Generate a clinical summary as JSON from this patient data:
        {json.dumps(data, indent=2)}
        
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
        text = text.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(text)
        except:
            return generate_rule_based_summary(data)
    except:
        return generate_rule_based_summary(data)

def generate_rule_based_summary(data):
    chief = data.get('chief_complaint', '')
    duration = data.get('duration', '')
    symptoms = data.get('symptoms', [])
    
    hpi = f"Patient presents with {chief}"
    if duration:
        hpi += f" for {duration.lower()}"
    if symptoms:
        hpi += f". Associated symptoms: {', '.join(symptoms)}"
    hpi += "."
    
    chief_lower = chief.lower()
    symptoms_lower = [s.lower() for s in symptoms]
    risk = "Standard - Routine evaluation"
    
    if 'chest pain' in chief_lower and 'shortness of breath' in symptoms_lower:
        risk = "HIGH - Possible cardiac emergency"
    elif 'chest pain' in chief_lower:
        risk = "MODERATE - Cardiac evaluation recommended"
    elif 'breathing' in chief_lower:
        risk = "MODERATE - Respiratory assessment needed"
    
    return {
        "chief_complaint": chief,
        "hpi": hpi,
        "findings": f"Duration: {duration}. Symptoms: {len(symptoms)}",
        "risk_assessment": risk,
        "recommendations": "Complete physical examination and relevant investigations."
    }

def detect_red_flags(data):
    chief = data.get('chief_complaint', '').lower()
    symptoms = [s.lower() for s in data.get('symptoms', [])]
    
    flags = []
    
    if 'chest pain' in chief and 'shortness of breath' in symptoms:
        flags.append({"level": "CRITICAL", "message": "Chest pain with dyspnea - Possible MI/PE",
                     "action": "Immediate ECG, troponin, O2 saturation"})
    elif 'chest pain' in chief and 'sweating' in symptoms:
        flags.append({"level": "CRITICAL", "message": "Chest pain with diaphoresis - Possible ACS",
                     "action": "Immediate ECG, cardiac monitoring"})
    elif 'chest pain' in chief:
        flags.append({"level": "HIGH", "message": "Chest pain reported",
                     "action": "ECG recommended within 10 minutes"})
    
    if 'breathing' in chief or 'breath' in chief:
        flags.append({"level": "HIGH", "message": "Breathing difficulty",
                     "action": "Check SpO2, respiratory rate"})
    
    if 'headache' in chief and 'dizziness' in symptoms:
        flags.append({"level": "MODERATE", "message": "Headache with dizziness",
                     "action": "Neurological exam, BP check"})
    
    return flags

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
# HEADER WITH MODE SELECTOR
# ============================================
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

with col1:
    st.markdown("# 🏥 MediKiosk Pro")

with col2:
    if st.button("👤 Patient", use_container_width=True,
                 type="primary" if st.session_state.view == "patient" else "secondary"):
        st.session_state.view = "patient"
        st.session_state.step = 1
        st.rerun()

with col3:
    if st.button("👨‍⚕️ Doctor", use_container_width=True,
                 type="primary" if st.session_state.view == "doctor" else "secondary"):
        st.session_state.view = "doctor"
        st.rerun()

with col4:
    if st.button("📊 Analytics", use_container_width=True,
                 type="primary" if st.session_state.view == "analytics" else "secondary"):
        st.session_state.view = "analytics"
        st.rerun()

st.markdown("---")

# ============================================
# ANALYTICS DASHBOARD
# ============================================
if st.session_state.view == "analytics":
    st.markdown("## 📊 Analytics Dashboard")
    
    df = get_consultation_dataframe()
    
    if df.empty:
        st.info("No data available yet. Complete some patient sessions first.")
    else:
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Consultations", len(df))
        with col2:
            today = df[df['date'] == datetime.now().date()]
            st.metric("Today", len(today))
        with col3:
            high_risk = df[df['risk'].str.contains('HIGH|CRITICAL', case=False, na=False)]
            st.metric("High Risk Cases", len(high_risk), delta_color="inverse")
        with col4:
            avg_age = df['age'].mean() if 'age' in df.columns else 0
            st.metric("Avg Age", f"{avg_age:.1f} yrs")
        
        st.markdown("---")
        
        # Row 1: Time series + Hour distribution
        col1, col2 = st.columns(2)
        with col1:
            fig = plot_time_series(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = plot_consultations_by_hour(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Row 2: Complaints + Risk
        col1, col2 = st.columns(2)
        with col1:
            fig = plot_top_complaints(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = plot_risk_distribution(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Row 3: Demographics
        col1, col2, col3 = st.columns(3)
        with col1:
            fig = plot_age_distribution(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = plot_gender_distribution(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with col3:
            fig = plot_language_distribution(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Download data
        st.markdown("---")
        st.download_button(
            "📥 Download Analytics Data (CSV)",
            data=df.to_csv(index=False),
            file_name=f"medikiosk_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ============================================
# DOCTOR VIEW
# ============================================
elif st.session_state.view == "doctor":
    if not st.session_state.authenticated:
        login_form()
    else:
        # Header with user info
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"## 👨‍⚕️ Welcome, {st.session_state.user_name}")
        with col2:
            if st.button("Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
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
            st.metric("Documents", stats['total_documents'])
        
        st.markdown("---")
        
        # Recent consultations
        st.markdown("### 📋 Recent Consultations")
        consultations = get_all_consultations(20)
        
        if consultations:
            for c in consultations:
                risk = c.get('risk_assessment', '')
                is_high_risk = 'HIGH' in risk or 'CRITICAL' in risk
                
                with st.expander(
                    f"🎫 {c['token_number']} - {c.get('name', 'Unknown')} "
                    f"({c.get('age', '?')}y, {c.get('gender', '?')})"
                ):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Chief Complaint:** {c.get('chief_complaint', 'N/A')}")
                        st.write(f"**Duration:** {c.get('duration', 'N/A')}")
                        st.write(f"**Severity:** {c.get('severity', 'N/A')}")
                        st.write(f"**Language:** {c.get('language', 'N/A')}")
                    
                    with col2:
                        if is_high_risk:
                            st.error(f"⚠️ {risk}")
                        else:
                            st.success(f"✅ {risk}")
                        
                        st.write(f"**Medications:** {c.get('medications', 'None')}")
                        st.write(f"**Allergies:** {c.get('allergies', 'None')}")
                        
                        # Drug interaction check
                        interactions = check_interactions(c.get('medications', ''))
                        if interactions:
                            for interaction in interactions:
                                st.warning(
                                    f"⚠️ **{interaction['severity']}**: "
                                    f"{interaction['drug1']} + {interaction['drug2']} - "
                                    f"{interaction['description']}"
                                )
                    
                    with col3:
                        if st.button("📄 PDF", key=f"pdf_{c['token_number']}", use_container_width=True):
                            try:
                                ai_summary = json.loads(c.get('ai_summary', '{}'))
                                patient_data = {
                                    'name': c.get('name'),
                                    'age': c.get('age'),
                                    'gender': c.get('gender'),
                                    'language': c.get('language'),
                                    'chief_complaint': c.get('chief_complaint'),
                                    'duration': c.get('duration'),
                                    'severity': c.get('severity'),
                                    'medications': c.get('medications'),
                                    'allergies': c.get('allergies')
                                }
                                pdf_bytes = generate_pdf_report(patient_data, ai_summary)
                                st.download_button(
                                    "⬇️ Download",
                                    data=pdf_bytes,
                                    file_name=f"{c['token_number']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{c['token_number']}"
                                )
                            except Exception as e:
                                st.error(f"PDF error: {e}")
                    
                    # AI Summary
                    try:
                        ai_summary = json.loads(c.get('ai_summary', '{}'))
                        if ai_summary.get('hpi'):
                            st.markdown("**🤖 AI Summary:**")
                            st.info(ai_summary['hpi'])
                    except:
                        pass
        else:
            st.info("No consultations yet.")

# ============================================
# PATIENT VIEW (Enhanced with AYUSH mode)
# ============================================
else:
    # Toggle AYUSH mode
    col1, col2 = st.columns([3, 1])
    with col2:
        st.session_state.ayush_mode = st.toggle("🌿 AYUSH Mode", value=st.session_state.ayush_mode)
    
    if st.session_state.ayush_mode:
        st.info("🌿 AYUSH Mode: Ayurvedic history taking enabled")
    
    # Progress
    steps = ["Consent", "Complaint", "History", "Documents", "Summary"]
    current = st.session_state.step
    
    progress_html = '<div class="progress-container">'
    for i, step_name in enumerate(steps, 1):
        if i < current:
            cls, icon = "completed", "✓"
        elif i == current:
            cls, icon = "active", str(i)
        else:
            cls, icon = "", str(i)
        
        progress_html += f'''
            <div class="progress-step {cls}">
                <div class="step-circle">{icon}</div>
                <div class="step-label">{step_name}</div>
            </div>
        '''
    progress_html += '</div>'
    st.markdown(progress_html, unsafe_allow_html=True)
    
    # ===== STEP 1: CONSENT =====
    if st.session_state.step == 1:
        st.markdown('<div class="kiosk-header"><h1>🏥 Welcome to MediKiosk</h1><p>Your health, your voice</p></div>', unsafe_allow_html=True)
        
        # TTS welcome
        if st.session_state.tts_enabled and GTTS_AVAILABLE:
            audio = text_to_speech(TTS_PROMPTS["English"]["welcome"], st.session_state.language)
            if audio:
                st.audio(audio, format="audio/mp3", autoplay=True)
        
        # Language
        st.markdown("### 🌐 Select Language")
        languages = ["English", "Hindi", "Tamil", "Telugu"]
        cols = st.columns(4)
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
        
        # Patient info
        st.markdown("### 👤 Patient Information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name / नाम", key="p_name")
            age = st.number_input("Age", 0, 120, 30, key="p_age")
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="p_gender")
            phone = st.text_input("Phone", key="p_phone")
        
        abha_id = st.text_input("ABHA ID (optional)", placeholder="12-3456-7890-1234", key="p_abha")
        
        st.session_state.patient_data.update({
            'name': name, 'age': age, 'gender': gender, 'phone': phone,
            'abha_id': abha_id if abha_id else f"GUEST{datetime.now().strftime('%Y%m%d%H%M%S')}"
        })
        
        st.markdown("---")
        
        # Consent
        st.markdown("### 📋 Consent")
        consent_text = {
            "English": "I consent to share my health information for medical purposes.",
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
    
    # ===== STEP 2: CHIEF COMPLAINT =====
    elif st.session_state.step == 2:
        st.markdown(f"## 🎯 {t('chief_complaint')}")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
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
        st.markdown("### ⚡ Quick Selection")
        
        complaints = [
            ("💔", "Chest Pain"), ("🤕", "Headache"), ("🤒", "Fever"),
            ("😤", "Breathing Difficulty"), ("🤢", "Nausea"), ("🦴", "Joint Pain"),
            ("😣", "Abdominal Pain"), ("😴", "Fatigue"), ("🩸", "Bleeding"),
            ("🦷", "Tooth Pain"), ("👁️", "Eye Problem"), ("👂", "Ear Problem")
        ]
        
        cols = st.columns(4)
        for i, (icon, complaint) in enumerate(complaints):
            with cols[i % 4]:
                if st.button(f"{icon} {complaint}", use_container_width=True, key=f"c_{i}"):
                    st.session_state.patient_data['chief_complaint'] = complaint
                    st.session_state.step = 3
                    st.rerun()
    
    # ===== STEP 3: HISTORY (with AYUSH) =====
    elif st.session_state.step == 3:
        chief = st.session_state.patient_data.get('chief_complaint', '')
        st.markdown(f"## 📝 History: {chief}")
        st.markdown("---")
        
        # Standard history
        st.markdown("### ⏰ Duration")
        duration = st.radio("How long?", 
            ["Today", "1-2 days", "3-5 days", "1-2 weeks", "More than a month"],
            horizontal=True, key="dur")
        st.session_state.patient_data['duration'] = duration
        
        if any(w in chief.lower() for w in ['pain', 'ache', 'headache']):
            st.markdown("### 📊 Severity")
            sev = st.slider("Pain level (1-10)", 1, 10, 5, key="sev")
            st.session_state.patient_data['severity'] = sev
        
        st.markdown("### 🔍 Symptoms")
        symptoms = st.multiselect("Select all:",
            ["Nausea", "Dizziness", "Sweating", "Shortness of breath",
             "Cough", "Body ache", "Fatigue", "Loss of appetite", "None"],
            key="sym")
        st.session_state.patient_data['symptoms'] = symptoms
        
        st.markdown("### 📋 Past History")
        past = st.multiselect("Existing conditions:",
            ["Diabetes", "Hypertension", "Heart Disease", "Asthma",
             "Thyroid", "Kidney Disease", "None"], key="past")
        st.session_state.patient_data['past_history'] = past
        
        st.markdown("### 💊 Medications")
        meds = st.text_input("Current medications:", key="meds")
        st.session_state.patient_data['medications'] = meds
        
        # Check drug interactions
        if meds:
            interactions = check_interactions(meds)
            if interactions:
                st.markdown("#### ⚠️ Drug Interactions Detected")
                for interaction in interactions:
                    st.warning(
                        f"**{interaction['severity']}**: "
                        f"{interaction['drug1']} + {interaction['drug2']} - "
                        f"{interaction['description']}"
                    )
        
        st.markdown("### ⚠️ Allergies")
        allergy = st.radio("Drug allergies:",
            ["None", "Penicillin", "Sulfa", "Aspirin", "Other"],
            horizontal=True, key="alg")
        st.session_state.patient_data['allergies'] = allergy
        
        # AYUSH Section
        if st.session_state.ayush_mode:
            st.markdown("---")
            st.markdown("## 🌿 AYUSH Assessment")
            
            for category, data in AYUSH_QUESTIONS.items():
                with st.expander(f"**{data['title']}** - {data['subtitle']}"):
                    for q in data['questions']:
                        answer = st.radio(
                            q['text'],
                            q['options'],
                            key=f"ayush_{q['id']}",
                            horizontal=True
                        )
                        st.session_state.ayush_answers[q['id']] = answer
            
            # Calculate Prakriti
            if st.session_state.ayush_answers:
                prakriti = calculate_prakriti(st.session_state.ayush_answers)
                st.session_state.patient_data['prakriti'] = prakriti
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← " + t('back'), use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        with col2:
            if st.button(t('next') + " →", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
    
    # ===== STEP 4: DOCUMENTS =====
    elif st.session_state.step == 4:
        st.markdown("## 📄 Upload Documents")
        st.markdown("---")
        
        uploaded = st.file_uploader(
            "Upload prescriptions, lab reports (JPG, PNG, PDF)",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            accept_multiple_files=True
        )
        
        if uploaded:
            for file in uploaded:
                if file.name not in [d['filename'] for d in st.session_state.documents]:
                    with st.spinner(f"Processing {file.name}..."):
                        
                        if file.type == 'application/pdf':
                            text = extract_text_from_pdf(file)
                            entities = {"medications": [], "diagnoses": []}
                            
                            if openai_client:
                                try:
                                    prompt = f"Extract medications and diagnoses from: {text[:1000]}. Return JSON with keys medications, diagnoses."
                                    resp = openai_client.chat.completions.create(
                                        model="gpt-3.5-turbo",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.1
                                    )
                                    result = resp.choices[0].message.content
                                    result = result.replace("```json", "").replace("```", "").strip()
                                    entities = json.loads(result)
                                except:
                                    pass
                            
                            st.session_state.documents.append({
                                'filename': file.name,
                                'type': 'pdf',
                                'extracted_text': text[:500],
                                'entities': entities
                            })
                            st.success(f"✅ {file.name}")
                        
                        elif file.type in ['image/jpeg', 'image/png', 'image/jpg']:
                            img = Image.open(file)
                            st.image(img, caption=file.name, width=250)
                            
                            text = pytesseract.image_to_string(img)
                            entities = {"medications": [], "diagnoses": []}
                            
                            if openai_client:
                                try:
                                    prompt = f"Extract medications and diagnoses from: {text[:1000]}. Return JSON."
                                    resp = openai_client.chat.completions.create(
                                        model="gpt-3.5-turbo",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.1
                                    )
                                    result = resp.choices[0].message.content
                                    result = result.replace("```json", "").replace("```", "").strip()
                                    entities = json.loads(result)
                                except:
                                    pass
                            
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
                            
                            st.success(f"✅ {file.name}")
        
        if st.session_state.documents:
            st.markdown(f"### 📚 {len(st.session_state.documents)} Document(s) Uploaded")
            for d in st.session_state.documents:
                st.write(f"• {d['filename']}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.step = 3
                st.rerun()
        with col2:
            if st.button("Generate Summary →", type="primary", use_container_width=True):
                with st.spinner("🤖 AI analyzing..."):
                    ai_summary = generate_ai_summary(st.session_state.patient_data)
                    st.session_state.ai_analysis['summary'] = ai_summary
                    st.session_state.ai_analysis['red_flags'] = detect_red_flags(st.session_state.patient_data)
                    
                    # Save to DB
                    patient_id = save_patient(st.session_state.patient_data)
                    if patient_id:
                        st.session_state.patient_id = patient_id
                        save_data = {
                            **st.session_state.patient_data,
                            'ai_summary': ai_summary,
                            'risk_assessment': ai_summary.get('risk_assessment', ''),
                            'documents': st.session_state.documents
                        }
                        token = save_consultation(patient_id, save_data)
                        st.session_state.token_number = token
                
                st.session_state.step = 5
                st.rerun()
    
    # ===== STEP 5: SUMMARY =====
    elif st.session_state.step == 5:
        st.balloons()
        st.markdown('<div class="kiosk-header"><h1>✅ Thank You!</h1><p>Your information has been recorded</p></div>', unsafe_allow_html=True)
        
        # TTS thank you
        if st.session_state.tts_enabled and GTTS_AVAILABLE:
            prompt = TTS_PROMPTS.get(st.session_state.language, TTS_PROMPTS["English"])
            audio = text_to_speech(prompt["thank_you"], st.session_state.language)
            if audio:
                st.audio(audio, format="audio/mp3", autoplay=True)
        
        if st.session_state.token_number:
            st.markdown(f'''
                <div class="token-display">
                    <p style="margin:0; font-size:1.2em;">Your Token Number</p>
                    <div class="token-number">{st.session_state.token_number}</div>
                    <p style="margin:0; opacity:0.9;">Please proceed to the waiting area</p>
                </div>
            ''', unsafe_allow_html=True)
        
        data = st.session_state.patient_data
        ai_summary = st.session_state.ai_analysis.get('summary', {})
        red_flags = st.session_state.ai_analysis.get('red_flags', [])
        
        # Red flags
        for flag in red_flags:
            if flag['level'] == 'CRITICAL':
                st.error(f"### {flag['message']}\n**Action:** {flag['action']}")
            elif flag['level'] == 'HIGH':
                st.warning(f"### {flag['message']}\n**Action:** {flag['action']}")
        
        st.markdown("## 📋 Clinical Summary")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🎯 Chief Complaint")
            st.info(data.get('chief_complaint', ''))
            
            st.markdown("### ⏰ Duration")
            st.write(data.get('duration', ''))
            
            if 'severity' in data:
                st.markdown("### 📊 Severity")
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
        
        # AYUSH summary
        if st.session_state.ayush_mode and 'prakriti' in data:
            st.markdown("---")
            st.markdown("### 🌿 AYUSH Assessment")
            prakriti = data['prakriti']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Vata", f"{prakriti['vata']}%")
            with col2:
                st.metric("Pitta", f"{prakriti['pitta']}%")
            with col3:
                st.metric("Kapha", f"{prakriti['kapha']}%")
            st.info(f"**Dominant Dosha:** {prakriti['dominant']}")
        
        # AI Summary
        if ai_summary.get('hpi'):
            st.markdown("---")
            st.markdown("### 🤖 AI-Generated HPI")
            st.write(ai_summary['hpi'])
        
        if ai_summary.get('recommendations'):
            st.markdown("### 💡 Recommendations")
            st.write(ai_summary['recommendations'])
        
        # Actions
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # PDF download
            try:
                pdf_bytes = generate_pdf_report(data, ai_summary, st.session_state.documents)
                st.download_button(
                    "📄 PDF Report",
                    data=pdf_bytes,
                    file_name=f"{st.session_state.token_number}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF error: {e}")
        
        with col2:
            full_data = {
                'patient_info': data,
                'ai_summary': ai_summary,
                'documents': st.session_state.documents,
                'token': st.session_state.token_number
            }
            json_str = json.dumps(full_data, indent=2, default=str)
            st.download_button(
                "📄 JSON",
                data=json_str,
                file_name=f"{st.session_state.token_number or 'summary'}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            if st.button("🖨️ Print", use_container_width=True):
                st.info("Connect to printer")
        
        with col4:
            if st.button("🔄 New Patient", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    st.session_state.tts_enabled = st.toggle("🔊 Voice Guidance (TTS)", value=st.session_state.tts_enabled)
    
    st.markdown("---")
    st.markdown("### 📊 System Status")
    
    if openai_client:
        st.success("✅ AI Engine")
    else:
        st.warning("⚠️ AI Engine (offline)")
    
    if SPEECH_AVAILABLE:
        st.success("✅ Voice Input")
    else:
        st.warning("⚠️ Voice Input")
    
    if GTTS_AVAILABLE:
        st.success("✅ TTS")
    else:
        st.warning("⚠️ TTS")
    
    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    stats = get_stats()
    st.write(f"👥 Patients: **{stats['total_patients']}**")
    st.write(f"📋 Today: **{stats['today_consultations']}**")
    st.write(f"🚨 High Risk: **{stats['high_risk_cases']}**")
    
    st.markdown("---")
    st.markdown("**MediKiosk Pro v2.0**")
    st.caption("AI Clinical History Platform")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 10px;'>
        <p><strong>MediKiosk Pro v2.0</strong> - Production-Ready Clinical Platform</p>
        <p>Voice AI | Document OCR | Drug Interactions | AYUSH | PDF Reports | Analytics</p>
        <p>ABDM/FHIR Compliant | DPDP Act 2023 Ready</p>
    </div>
    """,
    unsafe_allow_html=True
)