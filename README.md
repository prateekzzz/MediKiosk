# 🏥 MediKiosk Pro - AI Clinical History Platform

An AI-powered clinical history taking and document digitization platform for Indian hospitals, addressing the "first-mile" problem of ABDM integration.

## 🎯 Problem

- India's OPD consultations average **2 minutes** (among shortest globally)
- History-taking accounts for **70-80%** of correct diagnoses
- No point-of-entry mechanism exists for structured history capture
- AYUSH systems require even more extensive history (Prakriti, Vikriti, etc.)

## 💡 Solution

MediKiosk is a patient-facing software platform that:
1. **Captures comprehensive history** via voice + touch in multiple Indian languages
2. **Digitizes physical documents** using OCR and AI extraction
3. **Generates structured summaries** using LLM technology
4. **Integrates with ABDM** via FHIR resources
5. **Detects red flags** for immediate triage

## ✨ Features

### Patient Features
- 🎤 Multilingual voice input (English, Hindi, Tamil, Telugu)
- 📱 Touch-based UI for accessibility
- 📄 Document scanning with OCR
- 🤖 AI-powered clinical summaries
- 🚨 Automatic red flag detection
- 🌿 AYUSH mode (Ayurvedic history)
- 🔊 Voice guidance (TTS)
- 🎫 Token number generation

### Doctor Features
- 🔐 Secure login
- 📊 Real-time analytics dashboard
- 📋 Patient queue with risk highlighting
- 💊 Drug interaction alerts
- 📄 PDF report generation
- 📈 Charts and statistics

### Technical Features
- 💾 SQLite database persistence
- 🏥 FHIR/ABDM bundle generation
- 🔒 DPDP Act 2023 compliant
- 📱 Responsive design
- 🎨 Custom professional UI

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Tesseract OCR
- OpenAI API key (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/your-username/medikiosk.git
cd medikiosk

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "OPENAI_API_KEY=your_key_here" > .env

# Run the app
streamlit run app_advanced.py