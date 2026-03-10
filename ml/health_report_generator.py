"""
Comprehensive Health Report PDF Generator
Generates multilingual health reports with trends, analysis, and recommendations
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.widgets.markers import makeMarker
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
import io

# Brand colors
INFUSE_ORANGE = HexColor('#E55A00')
DARK_BLUE = HexColor('#1a365d')
LIGHT_GREY = HexColor('#f7f7f7')
SUCCESS_GREEN = HexColor('#22c55e')
WARNING_ORANGE = HexColor('#f59e0b')
DANGER_RED = HexColor('#ef4444')
INFO_BLUE = HexColor('#3b82f6')


class HealthReportGenerator:
    """
    Generates comprehensive health reports in PDF format
    Supports multiple languages and includes visualizations
    """
    
    LANGUAGES = {
        'en': {
            'title': 'Health Analysis Report',
            'patient_info': 'Patient Information',
            'summary': 'Executive Summary',
            'vitals': 'Vital Signs Analysis',
            'trends': 'Health Trends',
            'risks': 'Risk Assessment',
            'allopathic': 'Medical Recommendations',
            'ayurvedic': 'Ayurvedic Recommendations',
            'lifestyle': 'Lifestyle Suggestions',
            'disclaimer': 'Medical Disclaimer',
            'generated': 'Report Generated',
            'normal': 'Normal',
            'warning': 'Needs Attention',
            'critical': 'Urgent',
            'prakriti': 'Ayurvedic Constitution (Prakriti)',
            'dosha_balance': 'Dosha Balance'
        },
        'hi': {
            'title': 'स्वास्थ्य विश्लेषण रिपोर्ट',
            'patient_info': 'रोगी की जानकारी',
            'summary': 'सारांश',
            'vitals': 'महत्वपूर्ण संकेत विश्लेषण',
            'trends': 'स्वास्थ्य प्रवृत्तियां',
            'risks': 'जोखिम मूल्यांकन',
            'allopathic': 'चिकित्सा सिफारिशें',
            'ayurvedic': 'आयुर्वेदिक सिफारिशें',
            'lifestyle': 'जीवनशैली सुझाव',
            'disclaimer': 'चिकित्सा अस्वीकरण',
            'generated': 'रिपोर्ट निर्मित',
            'normal': 'सामान्य',
            'warning': 'ध्यान देने की आवश्यकता',
            'critical': 'तत्काल',
            'prakriti': 'आयुर्वेदिक प्रकृति',
            'dosha_balance': 'दोष संतुलन'
        },
        'ar': {
            'title': 'تقرير التحليل الصحي',
            'patient_info': 'معلومات المريض',
            'summary': 'ملخص تنفيذي',
            'vitals': 'تحليل العلامات الحيوية',
            'trends': 'الاتجاهات الصحية',
            'risks': 'تقييم المخاطر',
            'allopathic': 'التوصيات الطبية',
            'ayurvedic': 'توصيات الأيورفيدا',
            'lifestyle': 'اقتراحات نمط الحياة',
            'disclaimer': 'إخلاء المسؤولية الطبية',
            'generated': 'تم إنشاء التقرير',
            'normal': 'طبيعي',
            'warning': 'يحتاج اهتمام',
            'critical': 'عاجل',
            'prakriti': 'الدستور الأيورفيدي',
            'dosha_balance': 'توازن الدوشا'
        }
    }
    
    def __init__(self, language: str = 'en'):
        self.language = language if language in self.LANGUAGES else 'en'
        self.labels = self.LANGUAGES[self.language]
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup custom paragraph styles"""
        self.title_style = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=DARK_BLUE,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        self.heading_style = ParagraphStyle(
            'ReportHeading',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=INFUSE_ORANGE,
            spaceBefore=15,
            spaceAfter=10
        )
        
        self.subheading_style = ParagraphStyle(
            'ReportSubheading',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=DARK_BLUE,
            spaceBefore=10,
            spaceAfter=5
        )
        
        self.body_style = ParagraphStyle(
            'ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        self.bullet_style = ParagraphStyle(
            'ReportBullet',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceBefore=3,
            spaceAfter=3
        )
    
    def generate_report(self, 
                       patient_info: Dict,
                       health_summary: Dict,
                       vitals: Optional[Dict] = None,
                       trends: Optional[List[Dict]] = None,
                       risk_assessment: Optional[Dict] = None,
                       prakriti: Optional[Dict] = None,
                       allopathic_recommendations: Optional[List[str]] = None,
                       ayurvedic_recommendations: Optional[Dict] = None,
                       lifestyle_tips: Optional[List[str]] = None,
                       anomalies: Optional[Dict] = None) -> bytes:
        """
        Generate a comprehensive health report PDF
        
        Returns:
            PDF as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              topMargin=0.5*inch, bottomMargin=0.5*inch,
                              leftMargin=0.75*inch, rightMargin=0.75*inch)
        
        story = []
        
        # Title and header
        story.extend(self._create_header(patient_info))
        
        # Executive Summary
        story.extend(self._create_summary_section(health_summary))
        
        # Vitals Analysis
        if vitals:
            story.extend(self._create_vitals_section(vitals, anomalies))
        
        # Prakriti/Dosha Section
        if prakriti:
            story.extend(self._create_prakriti_section(prakriti))
        
        # Trends
        if trends:
            story.extend(self._create_trends_section(trends))
        
        # Risk Assessment
        if risk_assessment:
            story.extend(self._create_risk_section(risk_assessment))
        
        # Recommendations
        story.append(PageBreak())
        story.extend(self._create_recommendations_section(
            allopathic_recommendations,
            ayurvedic_recommendations,
            lifestyle_tips
        ))
        
        # Disclaimer
        story.extend(self._create_disclaimer())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    
    def _create_header(self, patient_info: Dict) -> List:
        """Create report header with patient info"""
        elements = []
        
        # Logo/Title
        elements.append(Paragraph(f"HealthTrack Pro", self.title_style))
        elements.append(Paragraph(self.labels['title'], 
                                 ParagraphStyle('Subtitle', fontSize=14, textColor=grey, alignment=TA_CENTER)))
        elements.append(Spacer(1, 20))
        
        # Patient Info Table
        info_data = [
            ['Name:', patient_info.get('name', 'N/A'), 'Report Date:', datetime.now().strftime('%Y-%m-%d')],
            ['Age:', str(patient_info.get('age', 'N/A')), 'Report ID:', patient_info.get('report_id', 'N/A')],
            ['Gender:', patient_info.get('gender', 'N/A'), 'Provider:', 'Infuse HealthTrack Pro']
        ]
        
        info_table = Table(info_data, colWidths=[1*inch, 1.5*inch, 1*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), LIGHT_GREY),
            ('BACKGROUND', (2, 0), (2, -1), LIGHT_GREY),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_summary_section(self, summary: Dict) -> List:
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph(self.labels['summary'], self.heading_style))
        
        # Overall status indicator
        status = summary.get('overall_status', 'good')
        status_color = SUCCESS_GREEN if status == 'good' else (WARNING_ORANGE if status == 'moderate' else DANGER_RED)
        status_text = self.labels['normal'] if status == 'good' else (self.labels['warning'] if status == 'moderate' else self.labels['critical'])
        
        status_para = Paragraph(
            f"<font color='{status_color.hexval()}'><b>Overall Health Status: {status_text.upper()}</b></font>",
            ParagraphStyle('Status', fontSize=12, alignment=TA_CENTER, spaceBefore=10, spaceAfter=10)
        )
        elements.append(status_para)
        
        # Summary text
        if 'text' in summary:
            elements.append(Paragraph(summary['text'], self.body_style))
        
        # Key findings
        if 'findings' in summary:
            elements.append(Paragraph("<b>Key Findings:</b>", self.body_style))
            for finding in summary['findings']:
                elements.append(Paragraph(f"• {finding}", self.bullet_style))
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_vitals_section(self, vitals: Dict, anomalies: Optional[Dict] = None) -> List:
        """Create vitals analysis section with visual indicators"""
        elements = []
        
        elements.append(Paragraph(self.labels['vitals'], self.heading_style))
        
        vitals_data = [['Metric', 'Value', 'Normal Range', 'Status']]
        
        vital_ranges = {
            'heart_rate': ('60-100 bpm', 60, 100),
            'blood_pressure_systolic': ('90-140 mmHg', 90, 140),
            'blood_pressure_diastolic': ('60-90 mmHg', 60, 90),
            'spo2': ('95-100%', 95, 100),
            'temperature': ('36.1-37.2°C', 36.1, 37.2),
            'bmi': ('18.5-24.9', 18.5, 24.9)
        }
        
        for metric, value in vitals.items():
            if metric in vital_ranges:
                range_str, low, high = vital_ranges[metric]
                if isinstance(value, (int, float)):
                    if low <= value <= high:
                        status = '✓ Normal'
                    elif value < low:
                        status = '↓ Low'
                    else:
                        status = '↑ High'
                else:
                    status = '-'
                
                vitals_data.append([
                    metric.replace('_', ' ').title(),
                    str(value),
                    range_str,
                    status
                ])
        
        if len(vitals_data) > 1:
            vitals_table = Table(vitals_data, colWidths=[2*inch, 1.2*inch, 1.5*inch, 1*inch])
            vitals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), INFUSE_ORANGE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(vitals_table)
        
        # Anomaly alerts
        if anomalies and (anomalies.get('critical_alerts') or anomalies.get('warnings')):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("<b>Alerts:</b>", self.body_style))
            
            for alert in anomalies.get('critical_alerts', []):
                elements.append(Paragraph(
                    f"<font color='red'>⚠️ CRITICAL: {alert['message']}</font>", 
                    self.bullet_style
                ))
            
            for warning in anomalies.get('warnings', []):
                elements.append(Paragraph(
                    f"<font color='orange'>⚡ WARNING: {warning['message']}</font>", 
                    self.bullet_style
                ))
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_prakriti_section(self, prakriti: Dict) -> List:
        """Create Ayurvedic constitution section"""
        elements = []
        
        elements.append(Paragraph(self.labels['prakriti'], self.heading_style))
        
        # Prakriti result
        prakriti_type = prakriti.get('prakriti', 'Vata-Pitta-Kapha')
        confidence = prakriti.get('confidence', 85)
        
        elements.append(Paragraph(
            f"<b>Your Constitution:</b> {prakriti_type} (Confidence: {confidence}%)",
            ParagraphStyle('Prakriti', fontSize=12, textColor=DARK_BLUE, spaceBefore=5, spaceAfter=10)
        ))
        
        # Dosha breakdown
        breakdown = prakriti.get('dosha_breakdown', {'Vata': 33, 'Pitta': 33, 'Kapha': 34})
        
        dosha_data = [['Dosha', 'Percentage', 'Characteristics']]
        dosha_chars = {
            'Vata': 'Air & Space - Movement, creativity, flexibility',
            'Pitta': 'Fire & Water - Metabolism, transformation, intellect',
            'Kapha': 'Earth & Water - Structure, stability, nurturing'
        }
        
        for dosha, pct in breakdown.items():
            dosha_data.append([dosha, f"{pct}%", dosha_chars.get(dosha, '')])
        
        dosha_table = Table(dosha_data, colWidths=[1*inch, 1*inch, 3.5*inch])
        dosha_table.setStyle(TableStyle([
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
        elements.append(dosha_table)
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_trends_section(self, trends: List[Dict]) -> List:
        """Create health trends section with charts"""
        elements = []
        
        elements.append(Paragraph(self.labels['trends'], self.heading_style))
        
        for trend in trends[:3]:  # Limit to 3 trends
            metric = trend.get('metric', 'Unknown')
            direction = trend.get('trend_direction', 'stable')
            change = trend.get('change_percentage', 0)
            
            # Trend indicator
            arrow = '→' if direction == 'stable' else ('↑' if direction == 'increasing' else '↓')
            color = SUCCESS_GREEN if direction == 'stable' else (WARNING_ORANGE if abs(change) > 10 else INFO_BLUE)
            
            elements.append(Paragraph(
                f"<b>{metric.replace('_', ' ').title()}:</b> {arrow} {direction.title()} ({change:+.1f}%)",
                ParagraphStyle('Trend', fontSize=10, textColor=color, spaceBefore=5)
            ))
            
            # Insights
            for insight in trend.get('insights', [])[:2]:
                elements.append(Paragraph(f"  • {insight}", self.bullet_style))
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_risk_section(self, risk: Dict) -> List:
        """Create risk assessment section"""
        elements = []
        
        elements.append(Paragraph(self.labels['risks'], self.heading_style))
        
        risk_level = risk.get('overall_risk', 'low')
        risk_color = SUCCESS_GREEN if risk_level == 'low' else (WARNING_ORANGE if risk_level == 'moderate' else DANGER_RED)
        
        elements.append(Paragraph(
            f"<font color='{risk_color.hexval()}'><b>Overall Risk Level: {risk_level.upper()}</b></font>",
            ParagraphStyle('Risk', fontSize=11, spaceBefore=5, spaceAfter=10)
        ))
        
        # Specific risks
        if 'cardiovascular' in risk:
            cvd = risk['cardiovascular']
            elements.append(Paragraph(f"• Cardiovascular Risk: {cvd.get('level', 'N/A')} ({cvd.get('percentage', 0)}%)", self.bullet_style))
        
        if 'diabetes' in risk:
            elements.append(Paragraph(f"• Diabetes Risk: {risk['diabetes'].get('level', 'N/A')}", self.bullet_style))
        
        if 'factors' in risk:
            elements.append(Paragraph("<b>Contributing Factors:</b>", self.body_style))
            for factor in risk['factors']:
                elements.append(Paragraph(f"  - {factor}", self.bullet_style))
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_recommendations_section(self, 
                                        allopathic: Optional[List[str]],
                                        ayurvedic: Optional[Dict],
                                        lifestyle: Optional[List[str]]) -> List:
        """Create recommendations section"""
        elements = []
        
        # Allopathic/Medical
        if allopathic:
            elements.append(Paragraph(self.labels['allopathic'], self.heading_style))
            for rec in allopathic:
                elements.append(Paragraph(f"• {rec}", self.bullet_style))
            elements.append(Spacer(1, 10))
        
        # Ayurvedic
        if ayurvedic:
            elements.append(Paragraph(self.labels['ayurvedic'], self.heading_style))
            
            if 'diet' in ayurvedic:
                elements.append(Paragraph("<b>Diet:</b>", self.subheading_style))
                for item in ayurvedic['diet'][:4]:
                    elements.append(Paragraph(f"• {item}", self.bullet_style))
            
            if 'herbs' in ayurvedic:
                elements.append(Paragraph("<b>Herbs:</b>", self.subheading_style))
                for item in ayurvedic['herbs'][:4]:
                    elements.append(Paragraph(f"• {item}", self.bullet_style))
            
            if 'yoga' in ayurvedic:
                elements.append(Paragraph("<b>Yoga:</b>", self.subheading_style))
                for item in ayurvedic['yoga'][:4]:
                    elements.append(Paragraph(f"• {item}", self.bullet_style))
            
            elements.append(Spacer(1, 10))
        
        # Lifestyle
        if lifestyle:
            elements.append(Paragraph(self.labels['lifestyle'], self.heading_style))
            for tip in lifestyle:
                elements.append(Paragraph(f"• {tip}", self.bullet_style))
        
        return elements
    
    def _create_disclaimer(self) -> List:
        """Create medical disclaimer"""
        elements = []
        
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(self.labels['disclaimer'], self.heading_style))
        
        disclaimer_text = """
        <b>IMPORTANT:</b> This report is generated by an AI-powered health analysis system and is intended 
        for informational purposes only. It does NOT constitute medical advice, diagnosis, or treatment. 
        Always seek the advice of your physician or other qualified health provider with any questions 
        you may have regarding a medical condition. Never disregard professional medical advice or delay 
        in seeking it because of information provided in this report.
        
        Ayurvedic recommendations are based on traditional knowledge and should be discussed with a 
        qualified Ayurvedic practitioner before implementation.
        """
        
        elements.append(Paragraph(disclaimer_text, 
                                 ParagraphStyle('Disclaimer', fontSize=8, textColor=grey, 
                                              alignment=TA_JUSTIFY, leading=10)))
        
        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"<i>{self.labels['generated']}: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"Powered by HealthTrack Pro | infuse-ai.in</i>",
            ParagraphStyle('Footer', fontSize=8, textColor=grey, alignment=TA_CENTER)
        ))
        
        return elements
    
    def save_report(self, pdf_bytes: bytes, output_path: str) -> str:
        """Save PDF report to file"""
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        return output_path


# Factory function
def create_health_report(patient_info: Dict,
                        health_data: Dict,
                        language: str = 'en') -> bytes:
    """
    Create a complete health report
    
    Args:
        patient_info: Patient details (name, age, gender)
        health_data: Complete health analysis data
        language: Report language (en, hi, ar)
    
    Returns:
        PDF as bytes
    """
    generator = HealthReportGenerator(language)
    
    return generator.generate_report(
        patient_info=patient_info,
        health_summary=health_data.get('summary', {}),
        vitals=health_data.get('vitals'),
        trends=health_data.get('trends'),
        risk_assessment=health_data.get('risk_assessment'),
        prakriti=health_data.get('prakriti'),
        allopathic_recommendations=health_data.get('allopathic_recommendations'),
        ayurvedic_recommendations=health_data.get('ayurvedic_recommendations'),
        lifestyle_tips=health_data.get('lifestyle_tips'),
        anomalies=health_data.get('anomalies')
    )
