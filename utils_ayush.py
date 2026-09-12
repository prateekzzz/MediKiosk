# AYUSH (Ayurveda) History Taking Module

AYUSH_QUESTIONS = {
    "prakriti": {
        "title": "Prakriti (Constitution)",
        "subtitle": "Body constitution assessment",
        "questions": [
            {
                "id": "body_frame",
                "text": "How would you describe your body frame?",
                "options": ["Thin/Light (Vata)", "Medium/Moderate (Pitta)", "Broad/Heavy (Kapha)"]
            },
            {
                "id": "skin_type",
                "text": "What is your skin type?",
                "options": ["Dry/Rough (Vata)", "Soft/Warm (Pitta)", "Thick/Oily (Kapha)"]
            },
            {
                "id": "hair_type",
                "text": "What is your hair type?",
                "options": ["Dry/Brittle (Vata)", "Fine/Early graying (Pitta)", "Thick/Oily (Kapha)"]
            },
            {
                "id": "appetite",
                "text": "How is your appetite?",
                "options": ["Irregular (Vata)", "Strong/Intense (Pitta)", "Low/Steady (Kapha)"]
            },
            {
                "id": "digestion",
                "text": "How is your digestion?",
                "options": ["Gas/Bloating (Vata)", "Acidity/Heartburn (Pitta)", "Slow/Heavy (Kapha)"]
            },
            {
                "id": "sleep",
                "text": "How is your sleep?",
                "options": ["Light/Interrupted (Vata)", "Moderate (Pitta)", "Deep/Long (Kapha)"]
            },
            {
                "id": "temperament",
                "text": "How would you describe your temperament?",
                "options": ["Active/Quick (Vata)", "Focused/Intense (Pitta)", "Calm/Relaxed (Kapha)"]
            },
            {
                "id": "weather_preference",
                "text": "Which weather do you prefer?",
                "options": ["Warm (Vata)", "Cool (Pitta)", "Warm & Dry (Kapha)"]
            }
        ]
    },
    "agni": {
        "title": "Agni (Digestive Fire)",
        "subtitle": "Digestive capacity assessment",
        "questions": [
            {
                "id": "hunger_pattern",
                "text": "How often do you feel hungry?",
                "options": ["Irregular", "Very often", "Rarely"]
            },
            {
                "id": "post_meal",
                "text": "How do you feel after meals?",
                "options": ["Bloated/Gassy", "Satisfied", "Heavy/Lethargic"]
            },
            {
                "id": "bowel",
                "text": "How are your bowel movements?",
                "options": ["Irregular/Dry", "Regular/Loose", "Regular/Heavy"]
            },
            {
                "id": "water_intake",
                "text": "How much water do you drink daily?",
                "options": ["Less than 1L", "1-2L", "More than 2L"]
            }
        ]
    },
    "ahara_vihara": {
        "title": "Ahara-Vihara (Diet & Lifestyle)",
        "subtitle": "Daily routine and habits",
        "questions": [
            {
                "id": "diet_type",
                "text": "What type of diet do you follow?",
                "options": ["Vegetarian", "Non-vegetarian", "Mixed", "Vegan"]
            },
            {
                "id": "meal_timing",
                "text": "How regular are your meal times?",
                "options": ["Very regular", "Somewhat regular", "Irregular"]
            },
            {
                "id": "sleep_time",
                "text": "What time do you usually sleep?",
                "options": ["Before 10 PM", "10 PM - 12 AM", "After 12 AM"]
            },
            {
                "id": "wake_time",
                "text": "What time do you usually wake up?",
                "options": ["Before 6 AM", "6-8 AM", "After 8 AM"]
            },
            {
                "id": "exercise",
                "text": "How often do you exercise?",
                "options": ["Daily", "3-4 times/week", "Rarely", "Never"]
            },
            {
                "id": "stress_level",
                "text": "How would you rate your stress level?",
                "options": ["Low", "Moderate", "High", "Very High"]
            },
            {
                "id": "mental_state",
                "text": "How is your mental state usually?",
                "options": ["Calm", "Anxious", "Irritable", "Depressed"]
            }
        ]
    }
}

def calculate_prakriti(answers: dict) -> dict:
    """Calculate Prakriti based on answers"""
    vata_score = 0
    pitta_score = 0
    kapha_score = 0
    
    for key, value in answers.items():
        if isinstance(value, str):
            if 'Vata' in value:
                vata_score += 1
            elif 'Pitta' in value:
                pitta_score += 1
            elif 'Kapha' in value:
                kapha_score += 1
    
    total = vata_score + pitta_score + kapha_score
    if total == 0:
        total = 1
    
    return {
        'vata': round((vata_score / total) * 100),
        'pitta': round((pitta_score / total) * 100),
        'kapha': round((kapha_score / total) * 100),
        'dominant': max(
            [('Vata', vata_score), ('Pitta', pitta_score), ('Kapha', kapha_score)],
            key=lambda x: x[1]
        )[0]
    }