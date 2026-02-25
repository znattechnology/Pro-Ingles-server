"""
Certificate Generation Service

This service handles the creation and management of course completion certificates.
It generates professional PDF certificates and handles storage (local or S3).
"""

import io
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.courses.models import CourseCertificate, Course
from apps.users.models import User


class CertificateGenerationService:
    """
    Service for generating course completion certificates as PDFs.
    """

    # Certificate dimensions (A4 Landscape)
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

    # Colors
    PRIMARY_COLOR = colors.HexColor('#6B21A8')  # Purple
    SECONDARY_COLOR = colors.HexColor('#7C3AED')  # Violet
    GOLD_COLOR = colors.HexColor('#D4AF37')  # Gold
    TEXT_COLOR = colors.HexColor('#1F2937')  # Dark gray
    LIGHT_TEXT = colors.HexColor('#6B7280')  # Light gray

    def __init__(self, certificate: CourseCertificate):
        """
        Initialize the certificate generation service.

        Args:
            certificate: The CourseCertificate model instance
        """
        self.certificate = certificate
        self.user = certificate.user
        self.course = certificate.course

    def generate_pdf(self) -> Tuple[bytes, str]:
        """
        Generate the certificate PDF.

        Returns:
            Tuple of (pdf_bytes, filename)
        """
        buffer = io.BytesIO()

        # Create PDF with custom canvas
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        self._draw_background(c)
        self._draw_border(c)
        self._draw_header(c)
        self._draw_content(c)
        self._draw_footer(c)
        self._draw_verification(c)

        c.save()

        pdf_bytes = buffer.getvalue()
        buffer.close()

        filename = f"certificate_{self.certificate.certificate_number}.pdf"

        return pdf_bytes, filename

    def _draw_background(self, c: canvas.Canvas):
        """Draw the certificate background with gradient effect."""
        # Light background
        c.setFillColor(colors.HexColor('#FAFAFA'))
        c.rect(0, 0, self.PAGE_WIDTH, self.PAGE_HEIGHT, fill=True, stroke=False)

        # Decorative corners
        self._draw_corner_decoration(c, 20, self.PAGE_HEIGHT - 20, 'top-left')
        self._draw_corner_decoration(c, self.PAGE_WIDTH - 20, self.PAGE_HEIGHT - 20, 'top-right')
        self._draw_corner_decoration(c, 20, 20, 'bottom-left')
        self._draw_corner_decoration(c, self.PAGE_WIDTH - 20, 20, 'bottom-right')

    def _draw_corner_decoration(self, c: canvas.Canvas, x: float, y: float, position: str):
        """Draw decorative corner elements."""
        c.saveState()
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2)

        size = 40

        if position == 'top-left':
            c.line(x, y, x + size, y)
            c.line(x, y, x, y - size)
        elif position == 'top-right':
            c.line(x, y, x - size, y)
            c.line(x, y, x, y - size)
        elif position == 'bottom-left':
            c.line(x, y, x + size, y)
            c.line(x, y, x, y + size)
        elif position == 'bottom-right':
            c.line(x, y, x - size, y)
            c.line(x, y, x, y + size)

        c.restoreState()

    def _draw_border(self, c: canvas.Canvas):
        """Draw certificate border."""
        margin = 30

        # Outer border
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(3)
        c.rect(margin, margin,
               self.PAGE_WIDTH - 2 * margin,
               self.PAGE_HEIGHT - 2 * margin,
               fill=False, stroke=True)

        # Inner border
        inner_margin = 40
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(1)
        c.rect(inner_margin, inner_margin,
               self.PAGE_WIDTH - 2 * inner_margin,
               self.PAGE_HEIGHT - 2 * inner_margin,
               fill=False, stroke=True)

    def _draw_header(self, c: canvas.Canvas):
        """Draw the certificate header."""
        center_x = self.PAGE_WIDTH / 2

        # Platform name at top (inside border - margin is 40px inner)
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 70, "PROENGLISH")

        # Certificate title
        c.setFillColor(self.GOLD_COLOR)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 115, "CERTIFICADO DE CONCLUSÃO")

        # Decorative line under title
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2)
        line_width = 300
        c.line(center_x - line_width/2, self.PAGE_HEIGHT - 130,
               center_x + line_width/2, self.PAGE_HEIGHT - 130)

    def _draw_content(self, c: canvas.Canvas):
        """Draw the main certificate content."""
        center_x = self.PAGE_WIDTH / 2

        # "This certifies that" text
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 14)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 170, "Este certificado atesta que")

        # Student name
        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 28)
        student_name = self.user.name or self.user.email.split('@')[0]
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 210, student_name.upper())

        # Decorative line under name
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(1)
        name_width = min(len(student_name) * 15, 400)
        c.line(center_x - name_width/2, self.PAGE_HEIGHT - 225,
               center_x + name_width/2, self.PAGE_HEIGHT - 225)

        # Completion text
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 14)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 260, "concluiu com êxito o curso")

        # Course name
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 22)
        course_title = self.course.title
        # Truncate if too long
        if len(course_title) > 50:
            course_title = course_title[:47] + "..."
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 315, course_title)

        # Grade information
        if self.certificate.final_grade is not None:
            c.setFillColor(self.TEXT_COLOR)
            c.setFont("Helvetica", 12)
            grade_text = f"Nota Final: {self.certificate.final_grade:.1f}% ({self.certificate.final_grade_letter})"
            c.drawCentredString(center_x, self.PAGE_HEIGHT - 350, grade_text)

        # Date
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 12)
        issue_date = self.certificate.issued_at.strftime("%d de %B de %Y")
        # Translate month names to Portuguese
        months_pt = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        for en, pt in months_pt.items():
            issue_date = issue_date.replace(en, pt)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 380, f"Emitido em {issue_date}")

    def _draw_footer(self, c: canvas.Canvas):
        """Draw the certificate footer with signatures."""
        # Signature line
        signature_y = 120
        signature_width = 150

        # Left signature (Course Instructor - optional)
        left_x = self.PAGE_WIDTH / 3
        c.setStrokeColor(self.TEXT_COLOR)
        c.setLineWidth(1)
        c.line(left_x - signature_width/2, signature_y,
               left_x + signature_width/2, signature_y)

        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 10)
        c.drawCentredString(left_x, signature_y - 15, "Instrutor do Curso")

        # Right signature (Platform)
        right_x = 2 * self.PAGE_WIDTH / 3
        c.line(right_x - signature_width/2, signature_y,
               right_x + signature_width/2, signature_y)
        c.drawCentredString(right_x, signature_y - 15, "ProEnglish")

    def _draw_verification(self, c: canvas.Canvas):
        """Draw verification information with logo."""
        # Draw logo in bottom left corner (inside the inner border which is at 40px)
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Logo_Preto.png')
        logo_x = 50  # 10px inside inner border
        logo_y = 50  # 10px above inner border
        logo_width = 60
        logo_height = 30

        if os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height,
                           preserveAspectRatio=True, mask='auto')
            except Exception:
                pass  # If logo fails to load, continue without it

        # Certificate number and verification code - positioned to the right of logo
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 8)

        text_x = logo_x + logo_width + 15  # Position text to the right of logo

        verification_text = f"Certificado Nº: {self.certificate.certificate_number}"
        c.drawString(text_x, logo_y + 18, verification_text)

        if self.certificate.verification_code:
            verify_text = f"Código de Verificação: {self.certificate.verification_code}"
            c.drawString(text_x, logo_y + 6, verify_text)

        # Verification URL - on the right side
        verify_url = f"Verificar em: proenglish.com/verify/{self.certificate.verification_code}"
        c.drawRightString(self.PAGE_WIDTH - 50, logo_y + 12, verify_url)

    def save_certificate(self) -> str:
        """
        Generate and save the certificate, returning the URL.

        Returns:
            The URL to the saved certificate PDF
        """
        pdf_bytes, filename = self.generate_pdf()

        # Determine save path
        cert_path = f"certificates/{self.user.id}/{filename}"

        # Save using Django's storage backend (handles both local and S3)
        saved_path = default_storage.save(cert_path, ContentFile(pdf_bytes))

        # Get the URL
        if hasattr(settings, 'USE_S3') and settings.USE_S3:
            certificate_url = default_storage.url(saved_path)
        else:
            certificate_url = f"{settings.MEDIA_URL}{saved_path}"

        # Update the certificate record
        self.certificate.certificate_url = certificate_url
        self.certificate.save(update_fields=['certificate_url'])

        return certificate_url


def generate_certificate_for_user(user: User, course: Course) -> Optional[CourseCertificate]:
    """
    Convenience function to generate a certificate for a user.

    Checks eligibility and creates the certificate if conditions are met.

    Args:
        user: The user to generate certificate for
        course: The course to generate certificate for

    Returns:
        The created CourseCertificate or None if not eligible
    """
    from apps.courses.services import GradeCalculatorService
    from apps.courses.models import CourseEnrollment, UserCourseProgress, StudentCourseGrade
    from apps.subscriptions.models import UserSubscription

    # P2 FIX: Check if user's subscription plan allows certificates
    try:
        subscription = UserSubscription.objects.select_related('plan').get(user=user)
        if not subscription.is_active() or not subscription.plan.certificates:
            return None
    except UserSubscription.DoesNotExist:
        return None

    # Check if already has certificate
    existing = CourseCertificate.objects.filter(user=user, course=course).first()
    if existing:
        return existing

    # Check enrollment
    if not CourseEnrollment.objects.filter(user=user, course=course).exists():
        return None

    # Check progress
    try:
        progress = UserCourseProgress.objects.get(user=user, course=course)
        if progress.overallProgress < 100.0:
            return None
    except UserCourseProgress.DoesNotExist:
        return None

    # Calculate/get grade
    calculator = GradeCalculatorService(user, course)
    grade = calculator.calculate_and_save(change_reason='certificate_check')

    # Check eligibility
    if not grade.is_eligible_for_certificate:
        return None

    # Generate verification code
    verification_code = f"VER-{uuid.uuid4().hex[:8].upper()}"

    # Create certificate
    certificate = CourseCertificate.objects.create(
        user=user,
        course=course,
        completion_percentage=progress.overallProgress,
        final_grade=grade.final_grade_percentage,
        final_grade_letter=grade.final_grade_letter,
        verification_code=verification_code
    )

    # Generate PDF
    service = CertificateGenerationService(certificate)
    service.save_certificate()

    return certificate
