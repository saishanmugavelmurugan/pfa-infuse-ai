"""
Marketing Campaigns & Pricing Generator for HealthTrack Pro
Generates professional PDF with platform-specific campaigns and pricing
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

router = APIRouter(prefix="/marketing", tags=["marketing"])

# Infuse-AI Brand Colors
INFUSE_ORANGE = colors.HexColor("#E55A00")
INFUSE_GOLD = colors.HexColor("#FF9A3B")
INFUSE_DARK = colors.HexColor("#1F2937")
INFUSE_GREEN = colors.HexColor("#059669")
WHATSAPP_GREEN = colors.HexColor("#25D366")
FACEBOOK_BLUE = colors.HexColor("#1877F2")
LINKEDIN_BLUE = colors.HexColor("#0A66C2")
INSTAGRAM_PINK = colors.HexColor("#E4405F")


def create_marketing_pdf():
    """Generate marketing campaigns and pricing PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=INFUSE_ORANGE,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=INFUSE_DARK,
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    subsection_style = ParagraphStyle(
        'SubsectionTitle',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=INFUSE_ORANGE,
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=INFUSE_DARK,
        spaceAfter=8,
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=INFUSE_DARK,
        leftIndent=15,
        spaceAfter=4
    )
    
    story = []
    
    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("HEALTHTRACK PRO", title_style))
    story.append(Paragraph("Marketing Campaign Strategy &amp; Pricing Guide", 
                          ParagraphStyle('Subtitle', fontSize=16, alignment=TA_CENTER, textColor=colors.gray)))
    story.append(Spacer(1, 0.5*inch))
    
    # Platform logos representation
    platforms_data = [
        ['WhatsApp', 'Facebook', 'LinkedIn', 'Instagram'],
    ]
    platforms_table = Table(platforms_data, colWidths=[1.3*inch]*4)
    platforms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), WHATSAPP_GREEN),
        ('BACKGROUND', (1, 0), (1, 0), FACEBOOK_BLUE),
        ('BACKGROUND', (2, 0), (2, 0), LINKEDIN_BLUE),
        ('BACKGROUND', (3, 0), (3, 0), INSTAGRAM_PINK),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(platforms_table)
    
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Prepared by: Infuse-AI Marketing Team", 
                          ParagraphStyle('Footer', fontSize=10, alignment=TA_CENTER, textColor=colors.gray)))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %Y')}", 
                          ParagraphStyle('Footer', fontSize=10, alignment=TA_CENTER, textColor=colors.gray)))
    story.append(Paragraph("www.infuse.net.in", 
                          ParagraphStyle('Footer', fontSize=10, alignment=TA_CENTER, textColor=INFUSE_ORANGE)))
    
    story.append(PageBreak())
    
    # ==================== TABLE OF CONTENTS ====================
    story.append(Paragraph("TABLE OF CONTENTS", section_style))
    
    toc_data = [
        ['Section', 'Page'],
        ['1. Executive Summary', '3'],
        ['2. WhatsApp Campaign Strategy', '4'],
        ['3. Facebook Campaign Strategy', '6'],
        ['4. LinkedIn Campaign Strategy', '8'],
        ['5. Instagram Campaign Strategy', '10'],
        ['6. Individual User Pricing', '12'],
        ['7. Enterprise Pricing', '14'],
        ['8. Global Competitive Analysis', '16'],
        ['9. ROI Projections', '17'],
    ]
    
    toc_table = Table(toc_data, colWidths=[4.5*inch, 1*inch])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(toc_table)
    
    story.append(PageBreak())
    
    # ==================== EXECUTIVE SUMMARY ====================
    story.append(Paragraph("1. EXECUTIVE SUMMARY", section_style))
    story.append(Paragraph(
        """HealthTrack Pro is positioned to capture the growing digital health market through targeted 
        social media campaigns across WhatsApp, Facebook, LinkedIn, and Instagram. Our pricing strategy 
        is designed to be globally competitive while ensuring profitability, with tiered offerings for 
        individual users and enterprises.""",
        body_style
    ))
    
    story.append(Paragraph("Market Opportunity", subsection_style))
    market_data = [
        ['Metric', 'Value'],
        ['Global Digital Health Market (2026)', '$550+ Billion'],
        ['India Healthcare App Users', '180+ Million'],
        ['YoY Growth Rate', '28.5%'],
        ['Target Market Penetration (Year 1)', '0.5%'],
        ['Revenue Target (Year 1)', '$2.5 Million'],
    ]
    market_table = Table(market_data, colWidths=[3*inch, 2.5*inch])
    market_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_GOLD),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(market_table)
    
    story.append(PageBreak())
    
    # ==================== WHATSAPP CAMPAIGN ====================
    story.append(Paragraph("2. WHATSAPP CAMPAIGN STRATEGY", section_style))
    
    # WhatsApp header
    wa_header = Table([['WhatsApp Business Campaign']], colWidths=[5.5*inch])
    wa_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHATSAPP_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(wa_header)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Campaign Objective", subsection_style))
    story.append(Paragraph(
        "Drive app downloads and user engagement through personalized health reminders, appointment notifications, "
        "and health tips via WhatsApp Business API. Focus on high-touch, conversational marketing.",
        body_style
    ))
    
    story.append(Paragraph("Target Audience", subsection_style))
    story.append(Paragraph("• Age 25-55, health-conscious individuals", bullet_style))
    story.append(Paragraph("• Existing patients of partner clinics", bullet_style))
    story.append(Paragraph("• Users who prefer vernacular languages (Hindi, Tamil, Telugu)", bullet_style))
    story.append(Paragraph("• Chronic disease patients needing regular monitoring", bullet_style))
    
    story.append(Paragraph("Campaign Messages (Templates)", subsection_style))
    
    wa_messages = [
        ['Message Type', 'Template', 'Frequency'],
        ['Welcome', '"Welcome to HealthTrack Pro! 🏥 Your personal health companion. Reply HELP for assistance."', 'Once'],
        ['Health Tip', '"💡 Daily Health Tip: Drink 8 glasses of water today! Track your hydration in the app."', 'Daily'],
        ['Appointment', '"📅 Reminder: Your appointment with Dr. {name} is tomorrow at {time}. Reply CONFIRM or RESCHEDULE"', 'As needed'],
        ['Lab Results', '"🔬 Your lab results are ready! View detailed analysis with AI insights in your HealthTrack Pro app."', 'As needed'],
        ['Medication', '"💊 Time for your {medication}! Stay consistent for better health outcomes."', '2-3x daily'],
    ]
    
    wa_table = Table(wa_messages, colWidths=[1*inch, 3.5*inch, 1*inch])
    wa_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), WHATSAPP_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(wa_table)
    
    story.append(Paragraph("Budget & KPIs", subsection_style))
    wa_budget = [
        ['Item', 'Monthly Cost', 'Expected Result'],
        ['WhatsApp Business API', '$500', 'Unlimited messages'],
        ['Template Approval', '$100', '10 templates'],
        ['Chatbot Integration', '$300', '24/7 support'],
        ['Total Monthly', '$900', '50,000+ engagements'],
    ]
    wa_budget_table = Table(wa_budget, colWidths=[2*inch, 1.5*inch, 2*inch])
    wa_budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#128C7E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(wa_budget_table)
    
    story.append(PageBreak())
    
    # ==================== FACEBOOK CAMPAIGN ====================
    story.append(Paragraph("3. FACEBOOK CAMPAIGN STRATEGY", section_style))
    
    fb_header = Table([['Facebook & Meta Ads Campaign']], colWidths=[5.5*inch])
    fb_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FACEBOOK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(fb_header)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Campaign Objective", subsection_style))
    story.append(Paragraph(
        "Build brand awareness and drive app installs through targeted Facebook and Instagram ads. "
        "Leverage Facebook's powerful targeting to reach health-conscious demographics and caregivers.",
        body_style
    ))
    
    story.append(Paragraph("Ad Formats & Creative Strategy", subsection_style))
    
    fb_ads = [
        ['Ad Format', 'Creative Concept', 'CTA', 'Budget %'],
        ['Video Ads (15-30s)', '"Your Health Journey Starts Here" - User testimonials, app walkthrough', 'Download Now', '40%'],
        ['Carousel Ads', 'Feature showcase: Lab Analysis → Doctor Consult → Wellness Tips → Wearable Sync', 'Learn More', '25%'],
        ['Lead Gen Ads', 'Free Health Assessment Quiz - Collect emails for nurturing', 'Take Quiz', '20%'],
        ['Retargeting Ads', 'Abandoned signup recovery, feature reminders', 'Complete Signup', '15%'],
    ]
    
    fb_table = Table(fb_ads, colWidths=[1.2*inch, 2.5*inch, 1*inch, 0.8*inch])
    fb_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), FACEBOOK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(fb_table)
    
    story.append(Paragraph("Audience Targeting", subsection_style))
    story.append(Paragraph("• Interest: Health & Fitness, Medical Apps, Yoga, Ayurveda, Wellness", bullet_style))
    story.append(Paragraph("• Demographics: 25-55 years, Urban India + NRI communities", bullet_style))
    story.append(Paragraph("• Behaviors: Health app users, Online shoppers, Engaged shoppers", bullet_style))
    story.append(Paragraph("• Lookalike: 1% lookalike of existing premium users", bullet_style))
    story.append(Paragraph("• Custom: Website visitors, App users (for retargeting)", bullet_style))
    
    story.append(Paragraph("Monthly Budget & Projections", subsection_style))
    fb_budget = [
        ['Campaign Phase', 'Monthly Budget', 'Expected Reach', 'Expected Installs', 'CPI'],
        ['Awareness (Month 1-2)', '$3,000', '500,000', '3,000', '$1.00'],
        ['Consideration (Month 3-4)', '$5,000', '800,000', '7,500', '$0.67'],
        ['Conversion (Month 5-6)', '$7,000', '600,000', '14,000', '$0.50'],
    ]
    fb_budget_table = Table(fb_budget, colWidths=[1.5*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch])
    fb_budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4267B2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(fb_budget_table)
    
    story.append(PageBreak())
    
    # ==================== LINKEDIN CAMPAIGN ====================
    story.append(Paragraph("4. LINKEDIN CAMPAIGN STRATEGY", section_style))
    
    li_header = Table([['LinkedIn B2B & Enterprise Campaign']], colWidths=[5.5*inch])
    li_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LINKEDIN_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(li_header)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Campaign Objective", subsection_style))
    story.append(Paragraph(
        "Generate B2B leads for enterprise healthcare solutions. Target HR directors, CHROs, hospital administrators, "
        "and corporate wellness managers for bulk licensing and white-label partnerships.",
        body_style
    ))
    
    story.append(Paragraph("Target Audience Segments", subsection_style))
    
    li_audience = [
        ['Segment', 'Job Titles', 'Company Size', 'Industries'],
        ['Corporate Wellness', 'CHRO, HR Director, Benefits Manager', '500+ employees', 'IT, BFSI, Manufacturing'],
        ['Healthcare Providers', 'Hospital Administrator, CIO, CMO', 'Any', 'Hospitals, Clinics, Diagnostics'],
        ['Insurance Partners', 'Product Head, Partnerships Director', 'Any', 'Health Insurance, TPA'],
        ['Pharma & Biotech', 'Digital Health Lead, Patient Engagement', '1000+ employees', 'Pharmaceuticals'],
    ]
    
    li_table = Table(li_audience, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 1.3*inch])
    li_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LINKEDIN_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(li_table)
    
    story.append(Paragraph("Content Strategy", subsection_style))
    story.append(Paragraph("• Thought Leadership: Weekly articles on digital health transformation, AI in healthcare", bullet_style))
    story.append(Paragraph("• Case Studies: ROI achieved by enterprise clients (anonymized)", bullet_style))
    story.append(Paragraph("• Whitepapers: 'Reducing Healthcare Costs with AI' - gated for lead gen", bullet_style))
    story.append(Paragraph("• Webinars: Monthly 'Future of Corporate Wellness' series", bullet_style))
    story.append(Paragraph("• Employee Advocacy: Leadership team sharing company updates", bullet_style))
    
    story.append(Paragraph("Ad Formats & Budget", subsection_style))
    li_budget = [
        ['Ad Type', 'Objective', 'Monthly Budget', 'Expected Leads', 'CPL'],
        ['Sponsored Content', 'Brand Awareness', '$2,000', '40', '$50'],
        ['Message Ads (InMail)', 'Direct Outreach', '$1,500', '30', '$50'],
        ['Lead Gen Forms', 'Whitepaper Downloads', '$2,500', '100', '$25'],
        ['Dynamic Ads', 'Retargeting', '$1,000', '20', '$50'],
        ['Total', '', '$7,000', '190', '$37 avg'],
    ]
    li_budget_table = Table(li_budget, colWidths=[1.3*inch, 1.3*inch, 1.1*inch, 1.1*inch, 0.7*inch])
    li_budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0077B5")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E8F4F8")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(li_budget_table)
    
    story.append(PageBreak())
    
    # ==================== INSTAGRAM CAMPAIGN ====================
    story.append(Paragraph("5. INSTAGRAM CAMPAIGN STRATEGY", section_style))
    
    ig_header = Table([['Instagram Visual & Influencer Campaign']], colWidths=[5.5*inch])
    ig_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), INSTAGRAM_PINK),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(ig_header)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Campaign Objective", subsection_style))
    story.append(Paragraph(
        "Build brand affinity among younger health-conscious audiences through visually appealing content, "
        "influencer partnerships, and user-generated content. Drive app downloads and engagement.",
        body_style
    ))
    
    story.append(Paragraph("Content Pillars", subsection_style))
    
    ig_content = [
        ['Pillar', 'Content Type', 'Frequency', 'Hashtags'],
        ['Health Tips', 'Carousel infographics, Reels', '5x/week', '#HealthTips #WellnessJourney'],
        ['App Features', 'Demo videos, Stories', '3x/week', '#HealthTrackPro #DigitalHealth'],
        ['User Stories', 'Testimonials, Before/After', '2x/week', '#HealthTransformation'],
        ['Doctor Insights', 'Expert Q&A, Live sessions', '1x/week', '#AskTheDoctor #HealthAdvice'],
        ['Ayurveda', 'Traditional remedies, Yoga', '3x/week', '#Ayurveda #HolisticHealth'],
    ]
    
    ig_table = Table(ig_content, colWidths=[1.1*inch, 1.8*inch, 0.9*inch, 1.7*inch])
    ig_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INSTAGRAM_PINK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(ig_table)
    
    story.append(Paragraph("Influencer Partnership Strategy", subsection_style))
    
    ig_influencers = [
        ['Tier', 'Follower Count', 'Budget/Post', 'Deliverables', 'Monthly Budget'],
        ['Mega', '1M+', '$2,000-5,000', '1 Reel + 2 Stories', '$5,000'],
        ['Macro', '100K-1M', '$500-1,500', '2 Reels + 3 Stories', '$4,000'],
        ['Micro', '10K-100K', '$100-400', '3 Posts + 5 Stories', '$3,000'],
        ['Nano', '1K-10K', '$50-100', 'UGC content', '$1,000'],
        ['Total Influencer Budget', '', '', '', '$13,000'],
    ]
    
    ig_inf_table = Table(ig_influencers, colWidths=[0.8*inch, 1*inch, 1*inch, 1.5*inch, 1.2*inch])
    ig_inf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#C13584")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FCE4EC")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(ig_inf_table)
    
    story.append(Paragraph("Paid Ads Budget", subsection_style))
    story.append(Paragraph("• Story Ads: $2,000/month (swipe-up to app store)", bullet_style))
    story.append(Paragraph("• Reels Ads: $3,000/month (highest engagement)", bullet_style))
    story.append(Paragraph("• Explore Ads: $1,500/month (discovery)", bullet_style))
    story.append(Paragraph("• Shopping Ads: $500/month (premium plans)", bullet_style))
    story.append(Paragraph("• Total Paid: $7,000/month", bullet_style))
    
    story.append(PageBreak())
    
    # ==================== INDIVIDUAL PRICING ====================
    story.append(Paragraph("6. INDIVIDUAL USER PRICING", section_style))
    
    story.append(Paragraph(
        "Competitive pricing designed for the global market, with special consideration for emerging markets. "
        "All prices are monthly; annual plans offer 2 months free.",
        body_style
    ))
    
    story.append(Paragraph("Individual Plans Comparison", subsection_style))
    
    individual_pricing = [
        ['Feature', 'Free', 'Basic', 'Pro', 'Premium'],
        ['Price (Monthly)', '$0', '$4.99', '$9.99', '$19.99'],
        ['Price (Annual/mo)', '$0', '$3.99', '$7.99', '$16.99'],
        ['Lab Report Analysis', '3/month', '10/month', 'Unlimited', 'Unlimited'],
        ['AI Health Insights', 'Basic', 'Standard', 'Advanced', 'Premium + Predictive'],
        ['Doctor Consultations', '—', '1/month', '3/month', 'Unlimited'],
        ['Wearable Sync', '1 device', '2 devices', '5 devices', 'Unlimited'],
        ['Ayurvedic Recommendations', '—', 'Basic', 'Full', 'Full + Personalized'],
        ['Medication Reminders', '3', '10', 'Unlimited', 'Unlimited'],
        ['Family Members', '—', '—', '2', '5'],
        ['Health Score Tracking', '✓', '✓', '✓', '✓'],
        ['Data Export', '—', 'PDF', 'PDF + Excel', 'FHIR + All formats'],
        ['Priority Support', '—', '—', 'Email', '24/7 Chat + Call'],
        ['Ad-Free Experience', '—', '✓', '✓', '✓'],
    ]
    
    ind_table = Table(individual_pricing, colWidths=[1.6*inch, 0.9*inch, 0.9*inch, 1*inch, 1.1*inch])
    ind_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#FFF5EB")),
        ('BACKGROUND', (-1, 0), (-1, -1), colors.HexColor("#FFF0E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, INFUSE_ORANGE),
    ]))
    story.append(ind_table)
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Regional Pricing (PPP Adjusted)", subsection_style))
    
    regional_pricing = [
        ['Region', 'Free', 'Basic', 'Pro', 'Premium', 'Currency'],
        ['India', '₹0', '₹149', '₹349', '₹699', 'INR'],
        ['USA/Canada', '$0', '$4.99', '$9.99', '$19.99', 'USD'],
        ['Europe', '€0', '€4.49', '€8.99', '€17.99', 'EUR'],
        ['UK', '£0', '£3.99', '£7.99', '£15.99', 'GBP'],
        ['Middle East', '$0', '$4.99', '$9.99', '$19.99', 'USD'],
        ['SEA', '$0', '$2.99', '$5.99', '$11.99', 'USD'],
        ['LATAM', '$0', '$2.99', '$5.99', '$11.99', 'USD'],
        ['Africa', '$0', '$1.99', '$3.99', '$7.99', 'USD'],
    ]
    
    reg_table = Table(regional_pricing, colWidths=[1.1*inch, 0.7*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.8*inch])
    reg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_GOLD),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(reg_table)
    
    story.append(PageBreak())
    
    # ==================== ENTERPRISE PRICING ====================
    story.append(Paragraph("7. ENTERPRISE PRICING", section_style))
    
    story.append(Paragraph(
        "Flexible enterprise pricing designed for hospitals, corporates, insurance companies, and healthcare providers. "
        "Volume discounts and custom integrations available.",
        body_style
    ))
    
    story.append(Paragraph("Enterprise Plans", subsection_style))
    
    enterprise_pricing = [
        ['Feature', 'Starter', 'Business', 'Enterprise', 'Custom'],
        ['Users', 'Up to 100', 'Up to 500', 'Up to 2,000', 'Unlimited'],
        ['Price/User/Month', '$3.00', '$2.50', '$2.00', 'Contact Us'],
        ['Minimum Monthly', '$300', '$1,000', '$3,000', '$10,000+'],
        ['Annual Contract', '$3,000', '$10,000', '$30,000', 'Custom'],
        ['Admin Dashboard', '✓', '✓', '✓', '✓'],
        ['SSO Integration', '—', '✓', '✓', '✓'],
        ['API Access', 'Basic', 'Standard', 'Full', 'Custom'],
        ['White-Label Option', '—', '—', '✓', '✓'],
        ['Custom Integrations', '—', '1', '3', 'Unlimited'],
        ['Dedicated Support', 'Email', 'Email + Chat', 'Phone + Slack', 'Dedicated CSM'],
        ['SLA Guarantee', '99%', '99.5%', '99.9%', '99.99%'],
        ['Data Residency', 'Standard', 'Choice of 3', 'Any Region', 'On-Premise Option'],
        ['Training Sessions', '1', '3', '10', 'Unlimited'],
        ['Compliance Reports', 'Standard', 'Detailed', 'Custom', 'Real-time'],
    ]
    
    ent_table = Table(enterprise_pricing, colWidths=[1.5*inch, 1*inch, 1*inch, 1.1*inch, 1*inch])
    ent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_DARK),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#F3F4F6")),
        ('BACKGROUND', (-1, 0), (-1, -1), colors.HexColor("#DBEAFE")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, INFUSE_DARK),
    ]))
    story.append(ent_table)
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Industry-Specific Packages", subsection_style))
    
    industry_pricing = [
        ['Industry', 'Package Name', 'Starting Price', 'Key Features'],
        ['Hospitals', 'HealthTrack Hospital', '$5,000/mo', 'EMR Integration, Patient Portal, Analytics'],
        ['Corporates', 'HealthTrack Corporate', '$2,000/mo', 'Employee Wellness, Health Camps, Reports'],
        ['Insurance', 'HealthTrack Insure', '$3,000/mo', 'Claims Integration, Risk Scoring, Fraud Detection'],
        ['Clinics', 'HealthTrack Clinic', '$500/mo', 'Appointment Booking, Prescription, Billing'],
        ['Diagnostics', 'HealthTrack Labs', '$1,500/mo', 'LIMS Integration, Auto-Upload, AI Analysis'],
        ['Pharma', 'HealthTrack Pharma', '$10,000/mo', 'Patient Support Program, Adherence Tracking'],
    ]
    
    ind_ent_table = Table(industry_pricing, colWidths=[1*inch, 1.5*inch, 1.1*inch, 2*inch])
    ind_ent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(ind_ent_table)
    
    story.append(PageBreak())
    
    # ==================== COMPETITIVE ANALYSIS ====================
    story.append(Paragraph("8. GLOBAL COMPETITIVE ANALYSIS", section_style))
    
    story.append(Paragraph(
        "HealthTrack Pro is positioned competitively against global and regional players while offering superior value.",
        body_style
    ))
    
    competitive = [
        ['Competitor', 'Region', 'Basic Plan', 'Pro Plan', 'Our Advantage'],
        ['MyFitnessPal', 'Global', '$9.99', '$19.99', 'Lab analysis + Ayurveda'],
        ['Practo', 'India', '₹199', '₹499', 'AI insights + Wearables'],
        ['1mg', 'India', '₹149', '₹299', 'Doctor consults + Holistic'],
        ['Headspace Health', 'Global', '$12.99', '$69.99', 'Physical + Mental health'],
        ['Apple Health+', 'Global', '$9.99', '—', 'Cross-platform + Ayurveda'],
        ['Samsung Health', 'Global', 'Free', '$4.99', 'Lab analysis + Doctor access'],
        ['Babylon Health', 'UK/Global', '£9.99', '£29.99', 'Lower price + India focus'],
        ['HealthTrack Pro', 'Global', '$4.99', '$9.99', 'Best value, comprehensive'],
    ]
    
    comp_table = Table(competitive, colWidths=[1.3*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.8*inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_DARK),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (3, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(comp_table)
    
    story.append(Paragraph("Our Competitive Advantages", subsection_style))
    story.append(Paragraph("• 30-50% lower pricing than Western competitors", bullet_style))
    story.append(Paragraph("• Unique Ayurveda + Allopathy dual approach", bullet_style))
    story.append(Paragraph("• AI-powered lab analysis (unique in India)", bullet_style))
    story.append(Paragraph("• ABDM integration for Indian market", bullet_style))
    story.append(Paragraph("• Multi-language support (12+ Indian languages)", bullet_style))
    story.append(Paragraph("• Comprehensive wearable ecosystem support", bullet_style))
    
    story.append(PageBreak())
    
    # ==================== ROI PROJECTIONS ====================
    story.append(Paragraph("9. ROI PROJECTIONS", section_style))
    
    story.append(Paragraph("Marketing Investment Summary", subsection_style))
    
    roi_summary = [
        ['Channel', 'Monthly Budget', 'Expected Users', 'CAC', 'LTV', 'ROI'],
        ['WhatsApp', '$900', '2,000', '$0.45', '$24', '53x'],
        ['Facebook/Meta', '$5,000', '7,500', '$0.67', '$24', '36x'],
        ['LinkedIn (B2B)', '$7,000', '190 leads', '$37', '$2,400', '65x'],
        ['Instagram', '$20,000', '15,000', '$1.33', '$24', '18x'],
        ['Total', '$32,900', '24,690 users', '$1.33 avg', '$24 avg', '18x avg'],
    ]
    
    roi_table = Table(roi_summary, colWidths=[1.1*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    roi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#D1FAE5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(roi_table)
    
    story.append(Paragraph("12-Month Revenue Projection", subsection_style))
    
    revenue_proj = [
        ['Quarter', 'New Users', 'Paying Users (10%)', 'ARPU', 'Revenue', 'Cumulative'],
        ['Q1', '50,000', '5,000', '$6', '$30,000', '$30,000'],
        ['Q2', '100,000', '15,000', '$7', '$105,000', '$135,000'],
        ['Q3', '200,000', '35,000', '$8', '$280,000', '$415,000'],
        ['Q4', '350,000', '70,000', '$9', '$630,000', '$1,045,000'],
        ['Year 1 Total', '700,000', '70,000', '$8 avg', '$1,045,000', '—'],
    ]
    
    rev_table = Table(revenue_proj, colWidths=[0.9*inch, 1*inch, 1.2*inch, 0.7*inch, 0.9*inch, 0.9*inch])
    rev_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INFUSE_GREEN),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#D1FAE5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(rev_table)
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Key Assumptions", subsection_style))
    story.append(Paragraph("• Free to Paid conversion: 10% (industry average: 5-15%)", bullet_style))
    story.append(Paragraph("• Monthly churn rate: 5% (target: <3% by Q4)", bullet_style))
    story.append(Paragraph("• Average Revenue Per User (ARPU): Growing from $6 to $9 as premium adoption increases", bullet_style))
    story.append(Paragraph("• Enterprise revenue not included (additional $500K+ potential)", bullet_style))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("—" * 50, ParagraphStyle('Line', alignment=TA_CENTER)))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')} | Contact: marketing@infuse.net.in | www.infuse.net.in",
        ParagraphStyle('Footer', fontSize=9, alignment=TA_CENTER, textColor=colors.gray)
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


@router.get("/campaigns-pricing-pdf")
async def get_marketing_pdf():
    """Download marketing campaigns and pricing PDF"""
    pdf_buffer = create_marketing_pdf()
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=HealthTrack_Pro_Marketing_Campaigns_Pricing_2026.pdf"
        }
    )


@router.get("/pricing/individual")
async def get_individual_pricing():
    """Get individual user pricing as JSON"""
    return {
        "currency": "USD",
        "plans": [
            {
                "name": "Free",
                "monthly_price": 0,
                "annual_price": 0,
                "features": ["3 lab reports/month", "Basic AI insights", "1 device sync", "Health score tracking"]
            },
            {
                "name": "Basic",
                "monthly_price": 4.99,
                "annual_price": 47.88,
                "features": ["10 lab reports/month", "1 doctor consult", "2 devices", "Ad-free", "PDF export"]
            },
            {
                "name": "Pro",
                "monthly_price": 9.99,
                "annual_price": 95.88,
                "features": ["Unlimited lab reports", "3 doctor consults", "5 devices", "2 family members", "Priority support"]
            },
            {
                "name": "Premium",
                "monthly_price": 19.99,
                "annual_price": 203.88,
                "features": ["Everything in Pro", "Unlimited consults", "5 family members", "Predictive AI", "24/7 support"]
            }
        ],
        "regional_pricing": {
            "IN": {"Basic": 149, "Pro": 349, "Premium": 699, "currency": "INR"},
            "US": {"Basic": 4.99, "Pro": 9.99, "Premium": 19.99, "currency": "USD"},
            "EU": {"Basic": 4.49, "Pro": 8.99, "Premium": 17.99, "currency": "EUR"},
            "UK": {"Basic": 3.99, "Pro": 7.99, "Premium": 15.99, "currency": "GBP"}
        }
    }


@router.get("/pricing/enterprise")
async def get_enterprise_pricing():
    """Get enterprise pricing as JSON"""
    return {
        "plans": [
            {
                "name": "Starter",
                "users": "Up to 100",
                "price_per_user": 3.00,
                "minimum_monthly": 300,
                "annual_contract": 3000
            },
            {
                "name": "Business", 
                "users": "Up to 500",
                "price_per_user": 2.50,
                "minimum_monthly": 1000,
                "annual_contract": 10000
            },
            {
                "name": "Enterprise",
                "users": "Up to 2,000",
                "price_per_user": 2.00,
                "minimum_monthly": 3000,
                "annual_contract": 30000
            },
            {
                "name": "Custom",
                "users": "Unlimited",
                "price_per_user": "Contact Us",
                "minimum_monthly": 10000,
                "annual_contract": "Custom"
            }
        ],
        "industry_packages": [
            {"industry": "Hospitals", "starting_price": 5000, "name": "HealthTrack Hospital"},
            {"industry": "Corporates", "starting_price": 2000, "name": "HealthTrack Corporate"},
            {"industry": "Insurance", "starting_price": 3000, "name": "HealthTrack Insure"},
            {"industry": "Clinics", "starting_price": 500, "name": "HealthTrack Clinic"},
            {"industry": "Diagnostics", "starting_price": 1500, "name": "HealthTrack Labs"},
            {"industry": "Pharma", "starting_price": 10000, "name": "HealthTrack Pharma"}
        ]
    }
