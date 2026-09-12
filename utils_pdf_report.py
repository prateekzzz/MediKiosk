from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io

def generate_pdf_report(patient_data: dict, ai_summary: dict, documents: list = None) -> bytes:
    """Generate professional PDF clinical summary"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=10,
        spaceBefore=15
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=8
    )
    
    # Build content
    content = []
    
    # Header
    content.append(Paragraph("MediKiosk Clinical Summary", title_style))
    content.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        body_style
    ))
    content.append(Spacer(1, 20))
    
    # Patient Info Table
    patient_info = [
        ['Field', 'Details'],
        ['Name', str(patient_data.get('name', 'Not provided'))],
        ['Age', str(patient_data.get('age', 'N/A'))],
        ['Gender', str(patient_data.get('gender', 'N/A'))],
        ['Language', str(patient_data.get('language', 'English'))],
        ['ABHA ID', str(patient_data.get('abha_id', 'Guest'))],
    ]
    
    patient_table = Table(patient_info, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f5f7fa')),
    ]))
    
    content.append(patient_table)
    content.append(Spacer(1, 20))
    
    # Chief Complaint
    content.append(Paragraph("Chief Complaint", heading_style))
    content.append(Paragraph(
        str(patient_data.get('chief_complaint', 'Not provided')),
        body_style
    ))
    
    # History of Present Illness
    content.append(Paragraph("History of Present Illness", heading_style))
    hpi = ai_summary.get('hpi', 'Not generated')
    content.append(Paragraph(str(hpi), body_style))
    
    # Duration & Severity
    content.append(Paragraph("Duration & Severity", heading_style))
    duration = patient_data.get('duration', 'Not specified')
    severity = patient_data.get('severity', 'N/A')
    content.append(Paragraph(f"Duration: {duration}", body_style))
    if severity != 'N/A':
        content.append(Paragraph(f"Severity: {severity}/10", body_style))
    
    # Symptoms
    symptoms = patient_data.get('symptoms', [])
    if symptoms:
        content.append(Paragraph("Associated Symptoms", heading_style))
        for symptom in symptoms:
            content.append(Paragraph(f"• {symptom}", body_style))
    
    # Past History
    past = patient_data.get('past_history', [])
    if past:
        content.append(Paragraph("Past Medical History", heading_style))
        for condition in past:
            content.append(Paragraph(f"• {condition}", body_style))
    
    # Medications
    content.append(Paragraph("Current Medications", heading_style))
    content.append(Paragraph(
        str(patient_data.get('medications', 'None') or 'None reported'),
        body_style
    ))
    
    # Allergies
    content.append(Paragraph("Allergies", heading_style))
    content.append(Paragraph(
        str(patient_data.get('allergies', 'None') or 'None reported'),
        body_style
    ))
    
    # Family History
    family = patient_data.get('family_history', [])
    if family:
        content.append(Paragraph("Family History", heading_style))
        for f in family:
            content.append(Paragraph(f"• {f}", body_style))
    
    # Risk Assessment
    content.append(Paragraph("Risk Assessment", heading_style))
    risk = ai_summary.get('risk_assessment', 'Standard')
    
    risk_color = '#4caf50'
    if 'CRITICAL' in str(risk).upper():
        risk_color = '#f44336'
    elif 'HIGH' in str(risk).upper():
        risk_color = '#ff9800'
    elif 'MODERATE' in str(risk).upper():
        risk_color = '#ffc107'
    
    risk_style = ParagraphStyle(
        'RiskStyle',
        parent=body_style,
        textColor=colors.HexColor(risk_color),
        fontSize=12,
        fontName='Helvetica-Bold'
    )
    content.append(Paragraph(str(risk), risk_style))
    
    # Recommendations
    if ai_summary.get('recommendations'):
        content.append(Paragraph("Recommendations", heading_style))
        content.append(Paragraph(str(ai_summary['recommendations']), body_style))
    
    # Documents
    if documents:
        content.append(Paragraph("Attached Documents", heading_style))
        for doc in documents:
            content.append(Paragraph(f"• {doc.get('filename', 'Document')}", body_style))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=body_style,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    content.append(Paragraph(
        "This is an AI-generated clinical summary. Physician verification required.",
        footer_style
    ))
    content.append(Paragraph(
        "Generated by MediKiosk | ABDM Compliant | DPDP Act 2023",
        footer_style
    ))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()