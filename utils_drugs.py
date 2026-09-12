# Drug interaction database (simplified for demo)
DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "MAJOR",
        "description": "Increased risk of bleeding",
        "action": "Avoid combination or monitor INR closely"
    },
    ("metformin", "alcohol"): {
        "severity": "MODERATE",
        "description": "Risk of lactic acidosis",
        "action": "Avoid alcohol"
    },
    ("ace_inhibitor", "potassium"): {
        "severity": "MAJOR",
        "description": "Risk of hyperkalemia",
        "action": "Monitor potassium levels"
    },
    ("ssri", "tramadol"): {
        "severity": "MAJOR",
        "description": "Risk of serotonin syndrome",
        "action": "Avoid combination"
    },
    ("statin", "grapefruit"): {
        "severity": "MODERATE",
        "description": "Increased statin levels",
        "action": "Avoid grapefruit juice"
    }
}

# Common drug classes mapping
DRUG_CLASSES = {
    "aspirin": "antiplatelet",
    "warfarin": "anticoagulant",
    "metformin": "antidiabetic",
    "amlodipine": "calcium_channel_blocker",
    "atenolol": "beta_blocker",
    "lisinopril": "ace_inhibitor",
    "atorvastatin": "statin",
    "omeprazole": "ppi",
    "paracetamol": "analgesic",
    "ibuprofen": "nsaid",
    "amoxicillin": "antibiotic",
    "azithromycin": "antibiotic",
    "cetirizine": "antihistamine",
    "pantoprazole": "ppi"
}

def check_interactions(medications_text: str):
    """Check for drug interactions"""
    if not medications_text:
        return []
    
    # Parse medications
    meds = []
    for med in medications_text.lower().replace(';', ',').split(','):
        med = med.strip()
        # Extract drug name (first word)
        if med:
            drug_name = med.split()[0]
            meds.append(drug_name)
    
    interactions = []
    
    # Check pairs
    for i, med1 in enumerate(meds):
        for med2 in meds[i+1:]:
            pair1 = (med1, med2)
            pair2 = (med2, med1)
            
            if pair1 in DRUG_INTERACTIONS:
                interaction = DRUG_INTERACTIONS[pair1]
                interactions.append({
                    'drug1': med1,
                    'drug2': med2,
                    **interaction
                })
            elif pair2 in DRUG_INTERACTIONS:
                interaction = DRUG_INTERACTIONS[pair2]
                interactions.append({
                    'drug1': med2,
                    'drug2': med1,
                    **interaction
                })
    
    return interactions

def get_drug_class(drug_name: str) -> str:
    """Get drug class"""
    return DRUG_CLASSES.get(drug_name.lower(), "unknown")