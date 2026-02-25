"""
Public API views for certificate verification.

These views are accessible without authentication.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.courses.models import CourseCertificate


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_certificate(request, verification_code):
    """
    Public endpoint to verify a certificate's authenticity.

    GET /api/v1/certificates/verify/{verification_code}/

    Returns certificate details if valid, or error if not found.
    This endpoint is public (no authentication required).
    """
    try:
        certificate = CourseCertificate.objects.select_related(
            'user', 'course'
        ).get(verification_code=verification_code)
    except CourseCertificate.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Certificado não encontrado',
            'message': 'O código de verificação fornecido não corresponde a nenhum certificado válido.'
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'valid': True,
        'message': 'Certificado válido e autêntico',
        'data': {
            'certificate_number': certificate.certificate_number,
            'student_name': certificate.user.name or 'Nome não disponível',
            'course_title': certificate.course.title,
            'issued_at': certificate.issued_at.isoformat(),
            'final_grade': {
                'percentage': certificate.final_grade,
                'letter': certificate.final_grade_letter,
            },
            'completion_percentage': certificate.completion_percentage,
        }
    })
