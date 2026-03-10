"""
DHA Compliance Documents Generator
Creates honest, accurate compliance assessment and pitch materials for Dubai Health Authority
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, grey, green, red, orange
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from datetime import datetime
import os

router = APIRouter(prefix="/dha-compliance", tags=["DHA Compliance"])

# Brand colors
INFUSE_ORANGE = HexColor('#E55A00')
INFUSE_LIGHT_ORANGE = HexColor('#FF9A3B')
DARK_BLUE = HexColor('#1a365d')
LIGHT_GREY = HexColor('#f7f7f7')
SUCCESS_GREEN = HexColor('#22c55e')
WARNING_ORANGE = HexColor('#f59e0b')
PENDING_BLUE = HexColor('#3b82f6')

# Actual compliance status based on codebase review
COMPLIANCE_STATUS = {
    "data_encryption": {
        "aes_256_at_rest": {"status": "PLANNED", "notes": "MongoDB encryption at rest to be configured on UAE deployment"},
        "tls_1_3_transit": {"status": "IMPLEMENTED", "notes": "HTTPS with TLS enabled via infrastructure"},
    },
    "access_control": {
        "rbac": {"status": "IMPLEMENTED", "notes": "Role-based access: user, doctor, admin roles implemented"},
        "mfa": {"status": "PLANNED", "notes": "MFA infrastructure designed, pending implementation"},
    },
    "interoperability": {
        "hl7_fhir": {"status": "PARTIAL", "notes": "FHIR R4 bundles implemented for ABDM, adaptable for NABIDH"},
        "nabidh_integration": {"status": "PLANNED", "notes": "Architecture ready, sandbox testing required"},
    },
    "patient_consent": {
        "consent_management": {"status": "IMPLEMENTED", "notes": "Digital consent flows with video consent option"},
        "audit_logging": {"status": "IMPLEMENTED", "notes": "Activity logging enabled across platform"},
    },
    "arabic_support": {
        "rtl_interface": {"status": "PARTIAL", "notes": "Language module includes Arabic translations"},
        "arabic_content": {"status": "PLANNED", "notes": "Full Arabic localization in roadmap"},
    },
    "data_residency": {
        "uae_hosting": {"status": "PLANNED", "notes": "Ready for UAE cloud deployment (AWS ME, Azure UAE)"},
        "data_localization": {"status": "PLANNED", "notes": "Architecture supports regional data isolation"},
    }
}


def create_compliance_assessment_pdf():
    """Generate honest compliance assessment document"""
    output_path = "/app/frontend/public/downloads/DHA_Compliance_Assessment_2026.pdf"
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=24, textColor=DARK_BLUE, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading1'], fontSize=16, textColor=INFUSE_ORANGE, spaceBefore=15, spaceAfter=10)
    subheading_style = ParagraphStyle('SubHeading', parent=styles['Heading2'], fontSize=12, textColor=DARK_BLUE, spaceBefore=10, spaceAfter=5)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY)
    
    story = []
    
    # Header
    story.append(Paragraph("HealthTrack Pro", title_style))
    story.append(Paragraph("DHA Compliance Assessment & Readiness Report", ParagraphStyle('Subtitle', fontSize=14, textColor=grey)))
    story.append(Paragraph(f"Document Date: {datetime.now().strftime('%B %d, %Y')}", ParagraphStyle('Date', fontSize=10, textColor=grey)))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(
        """This document provides an honest assessment of HealthTrack Pro's current compliance status 
        with Dubai Health Authority (DHA) requirements. We transparently identify implemented features, 
        partially implemented capabilities, and planned enhancements required for full NABIDH integration 
        and DHA licensing.""", body_style))
    story.append(Spacer(1, 15))
    
    # Compliance Status Table
    story.append(Paragraph("Current Compliance Status Overview", heading_style))
    
    status_data = [
        ["Requirement", "Status", "Details", "Timeline"]
    ]
    
    status_items = [
        ("AES-256 Encryption (At Rest)", "PLANNED", "MongoDB encryption ready for UAE deployment", "Q2 2026"),
        ("TLS 1.3 (In Transit)", "IMPLEMENTED", "HTTPS/TLS enabled via infrastructure", "Complete"),
        ("Role-Based Access Control", "IMPLEMENTED", "User, Doctor, Admin roles active", "Complete"),
        ("Multi-Factor Authentication", "PLANNED", "Architecture designed, implementation pending", "Q2 2026"),
        ("HL7 FHIR R4 Support", "PARTIAL", "FHIR bundles implemented, NABIDH adaptation needed", "Q2 2026"),
        ("NABIDH Integration", "PLANNED", "Ready for sandbox testing", "Q3 2026"),
        ("Patient Consent Management", "IMPLEMENTED", "Digital + Video consent flows", "Complete"),
        ("Audit Logging", "IMPLEMENTED", "Full activity logging enabled", "Complete"),
        ("Arabic Language Support", "PARTIAL", "Translations available, full RTL pending", "Q2 2026"),
        ("UAE Data Residency", "PLANNED", "Architecture supports UAE cloud hosting", "Q3 2026"),
    ]
    
    for item in status_items:
        status_color = SUCCESS_GREEN if item[1] == "IMPLEMENTED" else (WARNING_ORANGE if item[1] == "PARTIAL" else PENDING_BLUE)
        status_data.append([item[0], item[1], item[2], item[3]])
    
    status_table = Table(status_data, colWidths=[2*inch, 1*inch, 2.5*inch, 0.8*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 20))
    
    # What's Actually Implemented
    story.append(PageBreak())
    story.append(Paragraph("Implemented Features (Production Ready)", heading_style))
    
    implemented = [
        ["Feature", "Description", "Evidence"],
        ["JWT Authentication", "Secure token-based authentication with role validation", "routes/auth.py"],
        ["RBAC System", "Three-tier access: Patient, Doctor, Admin", "User model + middleware"],
        ["FHIR R4 Bundles", "Health records formatted per FHIR R4 standard", "routes/abdm.py"],
        ["Digital Consent", "Patient consent flows with timestamps", "routes/consent.py"],
        ["Video Consent", "Video-based consent recording capability", "routes/video_consent.py"],
        ["Audit Logging", "Activity tracking for compliance", "Multiple route files"],
        ["Patient Records", "Electronic health records management", "routes/medical_records.py"],
        ["Prescription System", "Digital prescriptions with drug database", "routes/prescriptions.py"],
        ["Telemedicine", "Video consultation infrastructure", "routes/telemedicine.py"],
        ["Lab Integration", "Lab test ordering and results", "routes/lab_tests.py"],
    ]
    
    impl_table = Table(implemented, colWidths=[1.5*inch, 3*inch, 1.8*inch])
    impl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SUCCESS_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0fff4')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(impl_table)
    story.append(Spacer(1, 20))
    
    # Gap Analysis
    story.append(Paragraph("Gap Analysis: Required for DHA Compliance", heading_style))
    
    gaps = [
        ["Gap", "Current State", "Required Action", "Priority"],
        ["UAE Data Residency", "Cloud-agnostic", "Deploy to UAE region (AWS ME/Azure UAE)", "HIGH"],
        ["NABIDH API Integration", "FHIR ready, not connected", "Complete sandbox testing & certification", "HIGH"],
        ["MFA Implementation", "Designed, not coded", "Implement TOTP/SMS 2FA", "HIGH"],
        ["Arabic RTL UI", "Translations exist", "Full RTL interface redesign", "MEDIUM"],
        ["DHA License Application", "Not started", "Register via Sheryan portal", "HIGH"],
        ["Penetration Testing", "Not performed", "Engage certified security auditor", "HIGH"],
        ["AES-256 at Rest", "Standard encryption", "Enable MongoDB encryption at rest", "HIGH"],
    ]
    
    gaps_table = Table(gaps, colWidths=[1.5*inch, 1.5*inch, 2.2*inch, 0.8*inch])
    gaps_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), WARNING_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#fffbeb')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(gaps_table)
    story.append(Spacer(1, 20))
    
    # Roadmap
    story.append(PageBreak())
    story.append(Paragraph("DHA Compliance Roadmap", heading_style))
    
    roadmap = [
        ["Phase", "Timeline", "Deliverables", "Status"],
        ["Phase 1: Infrastructure", "Q2 2026", "UAE cloud deployment, AES-256 encryption, MFA", "Planned"],
        ["Phase 2: Integration", "Q2-Q3 2026", "NABIDH sandbox testing, API certification", "Planned"],
        ["Phase 3: Localization", "Q3 2026", "Full Arabic support, RTL interface", "Planned"],
        ["Phase 4: Licensing", "Q3-Q4 2026", "Sheryan registration, DHA approval", "Planned"],
        ["Phase 5: Launch", "Q4 2026", "Production deployment in UAE", "Planned"],
    ]
    
    roadmap_table = Table(roadmap, colWidths=[1.3*inch, 1*inch, 2.8*inch, 0.9*inch])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(roadmap_table)
    story.append(Spacer(1, 20))
    
    # Commitment Statement
    story.append(Paragraph("Commitment to Compliance", heading_style))
    story.append(Paragraph(
        """Infuse HealthTrack Pro is committed to achieving full DHA compliance. This document 
        represents our transparent assessment of current capabilities and honest roadmap for 
        meeting all regulatory requirements. We welcome DHA consultation and guidance throughout 
        our compliance journey.""", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        """Contact: compliance@infuse.net.in | Website: infuse-ai.in""", 
        ParagraphStyle('Contact', fontSize=10, textColor=INFUSE_ORANGE)))
    
    doc.build(story)
    return output_path


def create_architecture_document():
    """Generate software architecture document for DHA submission"""
    output_path = "/app/frontend/public/downloads/DHA_Technical_Architecture_2026.pdf"
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=DARK_BLUE, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading1'], fontSize=14, textColor=INFUSE_ORANGE, spaceBefore=15, spaceAfter=10)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY)
    code_style = ParagraphStyle('Code', fontName='Courier', fontSize=8, leading=10, backColor=LIGHT_GREY)
    
    story = []
    
    # Header
    story.append(Paragraph("HealthTrack Pro", title_style))
    story.append(Paragraph("Technical Architecture Document for DHA Submission", ParagraphStyle('Subtitle', fontSize=12, textColor=grey)))
    story.append(Paragraph(f"Version 1.0 | {datetime.now().strftime('%B %Y')}", ParagraphStyle('Date', fontSize=10, textColor=grey)))
    story.append(Spacer(1, 20))
    
    # System Overview
    story.append(Paragraph("1. System Overview", heading_style))
    story.append(Paragraph(
        """HealthTrack Pro is a cloud-native healthcare platform built with modern, secure technologies. 
        The system follows a microservices architecture designed for scalability, security, and 
        regulatory compliance across multiple jurisdictions including UAE.""", body_style))
    story.append(Spacer(1, 15))
    
    # Technology Stack
    story.append(Paragraph("2. Technology Stack", heading_style))
    
    tech_stack = [
        ["Layer", "Technology", "Version", "Purpose"],
        ["Frontend", "React.js", "18.x", "Single Page Application with responsive UI"],
        ["UI Framework", "Tailwind CSS + Shadcn/UI", "3.x", "Modern, accessible component library"],
        ["Backend", "FastAPI (Python)", "0.100+", "High-performance async REST API"],
        ["Database", "MongoDB", "6.x", "Document database with encryption support"],
        ["Authentication", "JWT + bcrypt", "Latest", "Secure token-based auth with password hashing"],
        ["API Standard", "HL7 FHIR R4", "4.0.1", "Healthcare interoperability standard"],
        ["Hosting", "Kubernetes", "1.28+", "Container orchestration for scalability"],
        ["CDN/Proxy", "Cloudflare", "Enterprise", "DDoS protection, SSL termination"],
    ]
    
    tech_table = Table(tech_stack, colWidths=[1.2*inch, 1.5*inch, 0.8*inch, 2.5*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 20))
    
    # Security Architecture
    story.append(PageBreak())
    story.append(Paragraph("3. Security Architecture", heading_style))
    
    security_features = [
        ["Security Layer", "Implementation", "Standard"],
        ["Transport Security", "TLS 1.3 via HTTPS", "Industry Standard"],
        ["Data at Rest", "MongoDB Encryption (AES-256 planned)", "NIST"],
        ["Authentication", "JWT tokens with 24h expiry", "OAuth 2.0 compatible"],
        ["Password Storage", "bcrypt with salt rounds", "OWASP"],
        ["Access Control", "Role-Based (RBAC): User, Doctor, Admin", "NIST AC"],
        ["Session Management", "Secure HTTP-only cookies", "OWASP"],
        ["API Security", "Rate limiting, CORS, input validation", "OWASP API"],
        ["Audit Trail", "Comprehensive activity logging", "HIPAA/DHA"],
    ]
    
    sec_table = Table(security_features, colWidths=[1.5*inch, 2.5*inch, 1.5*inch])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 20))
    
    # Data Flow
    story.append(Paragraph("4. Data Flow Architecture", heading_style))
    story.append(Paragraph(
        """Patient data flows through the following secure pipeline:""", body_style))
    story.append(Spacer(1, 10))
    
    data_flow = [
        ["Step", "Process", "Security Measure"],
        ["1", "Patient enters data via web/mobile", "HTTPS, input validation"],
        ["2", "Frontend sends to API gateway", "TLS 1.3, CORS policy"],
        ["3", "JWT token validated", "Cryptographic verification"],
        ["4", "RBAC permission check", "Role-based authorization"],
        ["5", "Business logic processing", "Sanitized inputs, audit logging"],
        ["6", "Database read/write", "Encrypted connection, access control"],
        ["7", "Response to client", "Filtered data per role, HTTPS"],
    ]
    
    flow_table = Table(data_flow, colWidths=[0.5*inch, 2.5*inch, 2.5*inch])
    flow_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PENDING_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(flow_table)
    story.append(Spacer(1, 20))
    
    # FHIR/NABIDH Integration
    story.append(PageBreak())
    story.append(Paragraph("5. HL7 FHIR & NABIDH Integration Plan", heading_style))
    story.append(Paragraph(
        """HealthTrack Pro implements HL7 FHIR R4 standard for health data interoperability. 
        The existing FHIR implementation (developed for India's ABDM) provides a foundation 
        for NABIDH integration.""", body_style))
    story.append(Spacer(1, 10))
    
    fhir_resources = [
        ["FHIR Resource", "Status", "NABIDH Mapping"],
        ["Patient", "Implemented", "Patient Demographics"],
        ["Practitioner", "Implemented", "Healthcare Provider"],
        ["Observation", "Implemented", "Vital Signs, Lab Results"],
        ["DiagnosticReport", "Implemented", "Lab Reports"],
        ["MedicationRequest", "Implemented", "Prescriptions"],
        ["Encounter", "Implemented", "Visit Records"],
        ["Consent", "Implemented", "Patient Consent"],
        ["Bundle", "Implemented", "Document Packaging"],
    ]
    
    fhir_table = Table(fhir_resources, colWidths=[1.5*inch, 1.2*inch, 2.5*inch])
    fhir_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SUCCESS_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0fff4')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(fhir_table)
    story.append(Spacer(1, 20))
    
    # UAE Deployment Plan
    story.append(Paragraph("6. UAE Deployment Architecture", heading_style))
    story.append(Paragraph(
        """For UAE market entry, the following deployment architecture is planned:""", body_style))
    story.append(Spacer(1, 10))
    
    uae_plan = [
        ["Component", "UAE Solution", "Compliance Benefit"],
        ["Cloud Provider", "AWS Middle East (Bahrain) or Azure UAE", "Data residency in region"],
        ["Database", "MongoDB Atlas UAE region", "Data localization"],
        ["Encryption", "AWS KMS / Azure Key Vault", "AES-256 managed keys"],
        ["CDN", "Cloudflare ME PoP", "Low latency, DDoS protection"],
        ["Backup", "Cross-region UAE backup", "Disaster recovery"],
        ["Monitoring", "CloudWatch/Azure Monitor", "24/7 observability"],
    ]
    
    uae_table = Table(uae_plan, colWidths=[1.3*inch, 2.2*inch, 2*inch])
    uae_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(uae_table)
    story.append(Spacer(1, 20))
    
    # Contact
    story.append(Paragraph("7. Technical Contact", heading_style))
    story.append(Paragraph("""
    For technical inquiries regarding this architecture:<br/>
    <b>Email:</b> tech@infuse.net.in<br/>
    <b>Website:</b> infuse-ai.in<br/>
    <b>Documentation:</b> docs.infuse-ai.in
    """, body_style))
    
    doc.build(story)
    return output_path


def create_pitch_presentation():
    """Generate DHA partnership pitch presentation (PDF format)"""
    output_path = "/app/frontend/public/downloads/DHA_Partnership_Pitch_2026.pdf"
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), topMargin=0.3*inch, bottomMargin=0.3*inch)
    
    styles = getSampleStyleSheet()
    
    # Slide styles
    slide_title = ParagraphStyle('SlideTitle', fontSize=28, textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=20)
    slide_subtitle = ParagraphStyle('SlideSubtitle', fontSize=16, textColor=grey, alignment=TA_CENTER, spaceAfter=30)
    bullet_style = ParagraphStyle('Bullet', fontSize=14, leading=20, leftIndent=20)
    big_number = ParagraphStyle('BigNumber', fontSize=48, textColor=INFUSE_ORANGE, alignment=TA_CENTER)
    
    story = []
    
    # Slide 1: Title
    story.append(Spacer(1, 100))
    story.append(Paragraph("HealthTrack Pro", slide_title))
    story.append(Paragraph("DHA Partnership Proposal", slide_subtitle))
    story.append(Spacer(1, 50))
    story.append(Paragraph("Integrated Healthcare Platform for UAE", ParagraphStyle('TagLine', fontSize=18, textColor=INFUSE_ORANGE, alignment=TA_CENTER)))
    story.append(Spacer(1, 30))
    story.append(Paragraph("infuse-ai.in | infuse.net.in", ParagraphStyle('URL', fontSize=12, textColor=grey, alignment=TA_CENTER)))
    story.append(PageBreak())
    
    # Slide 2: Problem
    story.append(Paragraph("The Challenge", slide_title))
    story.append(Spacer(1, 30))
    problems = [
        "• Fragmented patient health records across providers",
        "• Limited integration between modern and traditional medicine",
        "• Manual, paper-based consent processes",
        "• Lack of AI-powered health insights for patients",
        "• Difficulty achieving NABIDH compliance for new platforms",
    ]
    for p in problems:
        story.append(Paragraph(p, bullet_style))
        story.append(Spacer(1, 10))
    story.append(PageBreak())
    
    # Slide 3: Solution
    story.append(Paragraph("Our Solution", slide_title))
    story.append(Spacer(1, 30))
    solutions = [
        "• <b>Unified Health Records</b> - Single view of patient health across providers",
        "• <b>Allopathic + Ayurvedic</b> - Integrated care from both medical systems",
        "• <b>Digital Consent</b> - Video-based consent with full audit trail",
        "• <b>AI Health Analysis</b> - GPT-5.2 powered insights from lab reports",
        "• <b>FHIR-Ready</b> - Built on HL7 FHIR R4 for NABIDH integration",
    ]
    for s in solutions:
        story.append(Paragraph(s, bullet_style))
        story.append(Spacer(1, 10))
    story.append(PageBreak())
    
    # Slide 4: Platform Features
    story.append(Paragraph("Platform Capabilities", slide_title))
    story.append(Spacer(1, 20))
    
    features = [
        ["Core Features", "Advanced Features", "Compliance Features"],
        ["Patient Registration", "AI Lab Report Analysis", "FHIR R4 Health Records"],
        ["Doctor Consultations", "Telemedicine Video Calls", "Digital Consent Management"],
        ["Prescription Management", "Wearable Data Integration", "Audit Logging"],
        ["Lab Test Ordering", "Multi-language Support", "Role-Based Access Control"],
        ["Appointment Booking", "Mobile App (iOS/Android)", "Encrypted Data Storage"],
    ]
    
    feat_table = Table(features, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
    feat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, white),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GREY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(feat_table)
    story.append(PageBreak())
    
    # Slide 5: DHA Compliance Roadmap
    story.append(Paragraph("DHA Compliance Roadmap", slide_title))
    story.append(Spacer(1, 20))
    
    roadmap = [
        ["Q2 2026", "Q3 2026", "Q4 2026"],
        ["UAE Cloud Deployment\nAES-256 Encryption\nMFA Implementation", 
         "NABIDH Sandbox Testing\nArabic Localization\nSheryan Registration", 
         "DHA Approval\nProduction Launch\nPartner Onboarding"],
    ]
    
    road_table = Table(roadmap, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
    road_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), PENDING_BLUE),
        ('BACKGROUND', (1, 0), (1, 0), WARNING_ORANGE),
        ('BACKGROUND', (2, 0), (2, 0), SUCCESS_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 2, white),
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_GREY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(road_table)
    story.append(PageBreak())
    
    # Slide 6: What We Need
    story.append(Paragraph("Partnership Request", slide_title))
    story.append(Spacer(1, 30))
    requests = [
        "• <b>DHA Consultation</b> - Guidance on NABIDH integration requirements",
        "• <b>Sandbox Access</b> - NABIDH sandbox environment for testing",
        "• <b>Technical Review</b> - Architecture validation by DHA Digital Health team",
        "• <b>Licensing Pathway</b> - Sheryan portal registration guidance",
        "• <b>Pilot Program</b> - Opportunity to pilot with DHA-licensed facilities",
    ]
    for r in requests:
        story.append(Paragraph(r, bullet_style))
        story.append(Spacer(1, 15))
    story.append(PageBreak())
    
    # Slide 7: Contact
    story.append(Spacer(1, 80))
    story.append(Paragraph("Let's Build Healthcare Together", slide_title))
    story.append(Spacer(1, 40))
    story.append(Paragraph("🌐 infuse-ai.in", ParagraphStyle('Contact', fontSize=20, alignment=TA_CENTER)))
    story.append(Spacer(1, 15))
    story.append(Paragraph("📧 partnerships@infuse.net.in", ParagraphStyle('Contact', fontSize=18, alignment=TA_CENTER, textColor=grey)))
    story.append(Spacer(1, 15))
    story.append(Paragraph("📱 Download: App Store | Play Store", ParagraphStyle('Contact', fontSize=16, alignment=TA_CENTER, textColor=grey)))
    story.append(Spacer(1, 40))
    story.append(Paragraph("Create your account at infuse.net.in", ParagraphStyle('CTA', fontSize=14, alignment=TA_CENTER, textColor=INFUSE_ORANGE)))
    
    doc.build(story)
    return output_path


@router.get("/generate-all")
async def generate_all_documents():
    """Generate all DHA compliance documents"""
    try:
        compliance_pdf = create_compliance_assessment_pdf()
        architecture_pdf = create_architecture_document()
        pitch_pdf = create_pitch_presentation()
        
        return {
            "success": True,
            "documents": {
                "compliance_assessment": "/downloads/DHA_Compliance_Assessment_2026.pdf",
                "technical_architecture": "/downloads/DHA_Technical_Architecture_2026.pdf",
                "partnership_pitch": "/downloads/DHA_Partnership_Pitch_2026.pdf"
            },
            "message": "All DHA documents generated successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/download/compliance")
async def download_compliance():
    """Download compliance assessment PDF"""
    file_path = create_compliance_assessment_pdf()
    return FileResponse(
        path=file_path,
        filename="DHA_Compliance_Assessment_2026.pdf",
        media_type="application/octet-stream"
    )


@router.get("/download/architecture")
async def download_architecture():
    """Download technical architecture PDF"""
    file_path = create_architecture_document()
    return FileResponse(
        path=file_path,
        filename="DHA_Technical_Architecture_2026.pdf",
        media_type="application/octet-stream"
    )


@router.get("/download/pitch")
async def download_pitch():
    """Download partnership pitch PDF"""
    file_path = create_pitch_presentation()
    return FileResponse(
        path=file_path,
        filename="DHA_Partnership_Pitch_2026.pdf",
        media_type="application/octet-stream"
    )
