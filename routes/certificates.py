"""
Compliance Certificate Generator for HealthTrack Pro
Generates professional PDF certificates for each compliance framework
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import os

router = APIRouter(prefix="/certificates", tags=["certificates"])

# Infuse-AI Brand Colors
INFUSE_ORANGE = colors.HexColor("#E55A00")
INFUSE_GOLD = colors.HexColor("#FF9A3B")
INFUSE_LIGHT_GOLD = colors.HexColor("#FFDA7B")
INFUSE_DARK = colors.HexColor("#1F2937")

# Certificate definitions
CERTIFICATES = {
    "soc2": {
        "title": "SOC 2 Type II",
        "full_name": "Service Organization Control 2 Type II",
        "status": "IN PROGRESS",
        "issuing_body": "Deloitte & Touche LLP (Planned)",
        "certificate_number": "ROADMAP-SOC2-2026",
        "issue_date": "Target: Q4 2026",
        "expiry_date": "To be determined",
        "scope": "Security, Availability, Processing Integrity, Confidentiality, and Privacy",
        "description": "Infuse-AI Technologies Pvt. Ltd. is actively working toward SOC 2 Type II certification covering the Trust Services Criteria for HealthTrack Pro.",
        "color": colors.HexColor("#4F46E5")
    },
    "hipaa": {
        "title": "HIPAA",
        "full_name": "Health Insurance Portability and Accountability Act",
        "status": "IN PROGRESS",
        "issuing_body": "HITRUST Alliance (Planned)",
        "certificate_number": "ROADMAP-HIPAA-2026",
        "issue_date": "Target: Q2 2026",
        "expiry_date": "To be determined",
        "scope": "Protected Health Information (PHI) handling, storage, and transmission",
        "description": "HealthTrack Pro is working toward HIPAA compliance for Privacy Rule, Security Rule, and Breach Notification requirements.",
        "color": colors.HexColor("#0891B2")
    },
    "gdpr": {
        "title": "GDPR",
        "full_name": "General Data Protection Regulation",
        "status": "IN PROGRESS",
        "issuing_body": "TÜV Rheinland (Planned)",
        "certificate_number": "ROADMAP-GDPR-2026",
        "issue_date": "Target: Q3 2026",
        "expiry_date": "To be determined",
        "scope": "Personal data processing of EU data subjects",
        "description": "HealthTrack Pro is implementing technical and organizational measures to achieve GDPR compliance for EU data subjects.",
        "color": colors.HexColor("#7C3AED")
    },
    "iso27001": {
        "title": "ISO 27001:2022",
        "full_name": "Information Security Management System",
        "status": "IN PROGRESS",
        "issuing_body": "BSI Group (Planned)",
        "certificate_number": "ROADMAP-ISO27001-2026",
        "issue_date": "Target: Q3 2026",
        "expiry_date": "To be determined",
        "scope": "Information Security Management System for healthcare data processing",
        "description": "Infuse-AI Technologies Pvt. Ltd. is building an Information Security Management System to conform to ISO/IEC 27001:2022.",
        "color": colors.HexColor("#059669")
    },
    "dpdp": {
        "title": "DPDP Act 2023",
        "full_name": "Digital Personal Data Protection Act, 2023",
        "status": "IN PROGRESS",
        "issuing_body": "Data Protection Board of India (Planned)",
        "certificate_number": "ROADMAP-DPDP-2026",
        "issue_date": "Target: Q2 2026",
        "expiry_date": "To be determined",
        "scope": "Personal data processing of Indian data principals",
        "description": "HealthTrack Pro is implementing compliance measures for the Digital Personal Data Protection Act, 2023 of India.",
        "color": colors.HexColor("#EA580C")
    },
    "abdm": {
        "title": "ABDM",
        "full_name": "Ayushman Bharat Digital Mission",
        "status": "IN PROGRESS",
        "issuing_body": "National Health Authority, India (Planned)",
        "certificate_number": "ROADMAP-ABDM-2026",
        "issue_date": "Target: Q1 2026",
        "expiry_date": "To be determined",
        "scope": "ABHA ID integration, Health Information Exchange, Consent Manager",
        "description": "HealthTrack Pro is working toward ABDM registration and certification for health data exchange in India.",
        "color": colors.HexColor("#DC2626")
    },
    "hl7fhir": {
        "title": "HL7 FHIR R4",
        "full_name": "Fast Healthcare Interoperability Resources",
        "status": "IN PROGRESS",
        "issuing_body": "HL7 International (Planned)",
        "certificate_number": "ROADMAP-FHIR-2026",
        "issue_date": "Target: Q2 2026",
        "expiry_date": "To be determined",
        "scope": "Patient, Observation, DiagnosticReport, MedicationRequest, Appointment resources",
        "description": "HealthTrack Pro is implementing HL7 FHIR R4 standards for healthcare data interoperability.",
        "color": colors.HexColor("#DB2777")
    },
    "zerotrust": {
        "title": "Zero Trust Security",
        "full_name": "Zero Trust Architecture Implementation",
        "status": "IMPLEMENTED",
        "issuing_body": "Infuse-AI Security Team",
        "certificate_number": "INTERNAL-ZT-2026",
        "issue_date": "January 1, 2026",
        "expiry_date": "Ongoing",
        "scope": "Network security, identity verification, micro-segmentation",
        "description": "HealthTrack Pro implements Zero Trust Architecture principles including 'never trust, always verify' for all access requests.",
        "color": colors.HexColor("#1F2937")
    }
}


def create_certificate_pdf(cert_key: str) -> BytesIO:
    """Generate a professional certificate PDF"""
    cert = CERTIFICATES.get(cert_key)
    if not cert:
        return None
    
    buffer = BytesIO()
    
    # Use landscape A4 for certificate
    page_width, page_height = landscape(A4)
    
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    # Background gradient effect (simplified)
    c.setFillColor(colors.HexColor("#FAFAFA"))
    c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
    
    # Decorative border
    c.setStrokeColor(cert["color"])
    c.setLineWidth(3)
    c.rect(30, 30, page_width - 60, page_height - 60, fill=False, stroke=True)
    
    # Inner border
    c.setStrokeColor(INFUSE_GOLD)
    c.setLineWidth(1)
    c.rect(40, 40, page_width - 80, page_height - 80, fill=False, stroke=True)
    
    # Corner decorations
    corner_size = 30
    c.setFillColor(cert["color"])
    # Top left
    c.rect(30, page_height - 30 - corner_size, corner_size, corner_size, fill=True, stroke=False)
    # Top right
    c.rect(page_width - 30 - corner_size, page_height - 30 - corner_size, corner_size, corner_size, fill=True, stroke=False)
    # Bottom left
    c.rect(30, 30, corner_size, corner_size, fill=True, stroke=False)
    # Bottom right
    c.rect(page_width - 30 - corner_size, 30, corner_size, corner_size, fill=True, stroke=False)
    
    # Header - "COMPLIANCE ROADMAP"
    c.setFillColor(cert["color"])
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - 80, "COMPLIANCE ROADMAP")
    
    # Certificate Title
    c.setFillColor(INFUSE_DARK)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_width / 2, page_height - 130, cert["title"])
    
    # Full name
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.gray)
    c.drawCentredString(page_width / 2, page_height - 155, cert["full_name"])
    
    # Status badge
    badge_width = 150
    badge_height = 35
    badge_x = (page_width - badge_width) / 2
    badge_y = page_height - 200
    
    c.setFillColor(cert["color"])
    c.roundRect(badge_x, badge_y, badge_width, badge_height, 5, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(page_width / 2, badge_y + 10, cert["status"])
    
    # "Working toward certification"
    c.setFillColor(INFUSE_DARK)
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_width / 2, page_height - 240, "Working toward certification for")
    
    # Company name
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(INFUSE_ORANGE)
    c.drawCentredString(page_width / 2, page_height - 275, "Infuse-AI Technologies Pvt. Ltd.")
    
    # Product name
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(INFUSE_DARK)
    c.drawCentredString(page_width / 2, page_height - 300, "HealthTrack Pro")
    
    # Description (wrapped)
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.gray)
    
    # Simple text wrapping
    description = cert["description"]
    max_width = 500
    words = description.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica", 11) < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    y_pos = page_height - 340
    for line in lines:
        c.drawCentredString(page_width / 2, y_pos, line)
        y_pos -= 15
    
    # Scope
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(INFUSE_DARK)
    c.drawCentredString(page_width / 2, y_pos - 20, "Scope:")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.gray)
    c.drawCentredString(page_width / 2, y_pos - 35, cert["scope"])
    
    # Certificate details table
    details_y = 140
    
    # Left column
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(INFUSE_DARK)
    c.drawString(80, details_y + 30, "Certificate Number:")
    c.drawString(80, details_y + 15, "Issue Date:")
    c.drawString(80, details_y, "Expiry Date:")
    
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.gray)
    c.drawString(180, details_y + 30, cert["certificate_number"])
    c.drawString(180, details_y + 15, cert["issue_date"])
    c.drawString(180, details_y, cert["expiry_date"])
    
    # Right column - Issuing Body
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(INFUSE_DARK)
    c.drawRightString(page_width - 80, details_y + 30, "Issuing Authority:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.gray)
    c.drawRightString(page_width - 80, details_y + 15, cert["issuing_body"])
    
    # Signature line
    sig_y = 85
    c.setStrokeColor(colors.gray)
    c.setLineWidth(0.5)
    c.line(page_width / 2 - 100, sig_y, page_width / 2 + 100, sig_y)
    
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.gray)
    c.drawCentredString(page_width / 2, sig_y - 12, "Authorized Signatory")
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.gray)
    c.drawCentredString(page_width / 2, 50, f"Verified at: https://infuse.net.in/compliance | Generated: {datetime.now().strftime('%B %d, %Y')}")
    
    # Infuse logo text
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(INFUSE_ORANGE)
    c.drawString(60, 50, "Infuse-AI")
    
    c.save()
    buffer.seek(0)
    return buffer


@router.get("/")
async def list_certificates():
    """List all available certificates"""
    certs = []
    for key, cert in CERTIFICATES.items():
        certs.append({
            "id": key,
            "title": cert["title"],
            "full_name": cert["full_name"],
            "status": cert["status"],
            "issuing_body": cert["issuing_body"],
            "certificate_number": cert["certificate_number"],
            "issue_date": cert["issue_date"],
            "expiry_date": cert["expiry_date"],
            "download_url": f"/api/certificates/{key}/download"
        })
    return {"certificates": certs}


@router.get("/{cert_id}/download")
async def download_certificate(cert_id: str):
    """Download a specific certificate as PDF"""
    if cert_id not in CERTIFICATES:
        return JSONResponse(
            status_code=404,
            content={"error": f"Certificate '{cert_id}' not found"}
        )
    
    pdf_buffer = create_certificate_pdf(cert_id)
    cert = CERTIFICATES[cert_id]
    
    filename = f"Infuse_HealthTrack_Pro_{cert['title'].replace(' ', '_').replace(':', '')}_Certificate.pdf"
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{cert_id}")
async def get_certificate_info(cert_id: str):
    """Get information about a specific certificate"""
    if cert_id not in CERTIFICATES:
        return JSONResponse(
            status_code=404,
            content={"error": f"Certificate '{cert_id}' not found"}
        )
    
    cert = CERTIFICATES[cert_id]
    return {
        "id": cert_id,
        "title": cert["title"],
        "full_name": cert["full_name"],
        "status": cert["status"],
        "issuing_body": cert["issuing_body"],
        "certificate_number": cert["certificate_number"],
        "issue_date": cert["issue_date"],
        "expiry_date": cert["expiry_date"],
        "scope": cert["scope"],
        "description": cert["description"],
        "download_url": f"/api/certificates/{cert_id}/download"
    }
