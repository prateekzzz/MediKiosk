import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = "medikiosk.db"


def init_database():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abha_id TEXT UNIQUE,
            name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            token_number TEXT,
            chief_complaint TEXT,
            duration TEXT,
            severity INTEGER,
            symptoms TEXT,
            past_history TEXT,
            medications TEXT,
            allergies TEXT,
            family_history TEXT,
            ai_summary TEXT,
            risk_assessment TEXT,
            documents TEXT,
            fhir_bundle TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER,
            filename TEXT,
            doc_type TEXT,
            extracted_text TEXT,
            entities TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (consultation_id) REFERENCES consultations (id)
        )
    """)

    conn.commit()
    conn.close()


def save_patient(patient_data: Dict) -> int:
    """Save patient and return ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO patients (abha_id, name, age, gender, phone, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            patient_data.get('abha_id'),
            patient_data.get('name'),
            patient_data.get('age'),
            patient_data.get('gender'),
            patient_data.get('phone'),
            patient_data.get('language')
        ))

        patient_id = cursor.lastrowid
        conn.commit()
        return patient_id

    except sqlite3.IntegrityError:
        cursor.execute(
            "SELECT id FROM patients WHERE abha_id = ?",
            (patient_data.get('abha_id'),)
        )

        result = cursor.fetchone()
        return result[0] if result else None

    finally:
        conn.close()


def save_consultation(patient_id: int, data: Dict) -> str:
    """Save consultation and return token number"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y%m%d")

    cursor.execute(
        "SELECT COUNT(*) FROM consultations "
        "WHERE DATE(created_at) = DATE('now')"
    )

    count = cursor.fetchone()[0] + 1
    token_number = f"MK{today}{count:04d}"

    cursor.execute("""
        INSERT INTO consultations (
            patient_id, token_number, chief_complaint, duration, severity,
            symptoms, past_history, medications, allergies, family_history,
            ai_summary, risk_assessment, documents, fhir_bundle
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        token_number,
        data.get('chief_complaint'),
        data.get('duration'),
        data.get('severity'),
        json.dumps(data.get('symptoms', [])),
        json.dumps(data.get('past_history', [])),
        data.get('medications'),
        data.get('allergies'),
        json.dumps(data.get('family_history', [])),
        json.dumps(data.get('ai_summary', {})),
        data.get('risk_assessment'),
        json.dumps(data.get('documents', [])),
        json.dumps(data.get('fhir_bundle', {}))
    ))

    conn.commit()
    conn.close()

    return token_number


def get_all_consultations(limit: int = 50) -> List[Dict]:
    """Get recent consultations"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, p.name, p.age, p.gender, p.abha_id
        FROM consultations c
        JOIN patients p ON c.patient_id = p.id
        ORDER BY c.created_at DESC
        LIMIT ?
    """, (limit,))

    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows


def get_consultation_by_token(token: str) -> Optional[Dict]:
    """Get consultation by token number"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, p.name, p.age, p.gender, p.abha_id
        FROM consultations c
        JOIN patients p ON c.patient_id = p.id
        WHERE c.token_number = ?
    """, (token,))

    row = cursor.fetchone()

    conn.close()

    return dict(row) if row else None


def get_stats() -> Dict:
    """Get dashboard statistics"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM patients")
    stats['total_patients'] = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM consultations "
        "WHERE DATE(created_at) = DATE('now')"
    )
    stats['today_consultations'] = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM consultations "
        "WHERE risk_assessment LIKE '%HIGH%' "
        "OR risk_assessment LIKE '%CRITICAL%'"
    )
    stats['high_risk_cases'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM documents")
    stats['total_documents'] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT language, COUNT(*) AS count
        FROM patients
        GROUP BY language
    """)

    stats['languages'] = [
        dict(row) for row in cursor.fetchall()
    ]

    cursor.execute("""
        SELECT chief_complaint, COUNT(*) AS count
        FROM consultations
        GROUP BY chief_complaint
        ORDER BY count DESC
        LIMIT 5
    """)

    stats['top_complaints'] = [
        dict(row) for row in cursor.fetchall()
    ]

    conn.close()

    return stats


init_database()
