"""
Email service for user verification and notifications.
"""

import random
from datetime import timedelta
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import EmailVerification


class EmailVerificationService:
    """Service for handling email verification codes."""
    
    @staticmethod
    def generate_verification_code():
        """Generate a 6-digit verification code."""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def create_verification_code(user, email=None):
        """
        Create a new verification code for a user.
        
        Args:
            user: User instance
            email: Email address (defaults to user.email)
            
        Returns:
            EmailVerification instance
        """
        if email is None:
            email = user.email
        
        # Invalidate any existing verification codes for this user/email
        EmailVerification.objects.filter(
            user=user,
            email=email,
            is_used=False
        ).update(is_used=True)
        
        # Generate new code
        code = EmailVerificationService.generate_verification_code()
        expires_at = timezone.now() + timedelta(minutes=30)  # 30 minutes expiry
        
        # Create verification record
        verification = EmailVerification.objects.create(
            user=user,
            code=code,
            email=email,
            expires_at=expires_at
        )
        
        return verification
    
    @staticmethod
    def send_verification_email(verification):
        """
        Send verification email to user.
        
        Args:
            verification: EmailVerification instance
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            subject = 'Verificação de Email - Tuwi'
            
            # Create email context
            context = {
                'user_name': verification.user.name,
                'user_email': verification.email,
                'verification_code': verification.code,
                'verification_url': f"{settings.FRONTEND_URL}/verify-email?email={verification.email}",
                'current_year': timezone.now().year,
                'frontend_url': settings.FRONTEND_URL,
            }
            
            # Render HTML template
            html_message = render_to_string('emails/email_verification.html', context)
            # Create plain text version
            text_message = strip_tags(html_message)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[verification.email],
            )
            msg.attach_alternative(html_message, "text/html")
            
            # Send email
            msg.send()
            
            return True
            
        except Exception as e:
            print(f"Error sending verification email: {e}")
            return False
    
    @staticmethod
    def verify_code(email, code):
        """
        Verify an email verification code.
        
        Args:
            email: Email address
            code: Verification code
            
        Returns:
            dict: Result with success status and user if valid
        """
        try:
            # Find the verification record
            verification = EmailVerification.objects.filter(
                email=email,
                code=code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not verification:
                return {
                    'success': False,
                    'error': 'Código inválido ou não encontrado',
                    'user': None
                }
            
            # Increment attempts
            verification.increment_attempts()
            
            # Check if code is valid
            if not verification.is_valid():
                if verification.is_expired():
                    return {
                        'success': False,
                        'error': 'Código expirado. Solicite um novo código.',
                        'user': None
                    }
                elif verification.attempts >= verification.max_attempts:
                    return {
                        'success': False,
                        'error': 'Muitas tentativas. Solicite um novo código.',
                        'user': None
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Código inválido',
                        'user': None
                    }
            
            # Mark as used
            verification.is_used = True
            verification.save()
            
            # Mark user email as verified
            user = verification.user
            user.email_verified = True
            user.save()
            
            return {
                'success': True,
                'error': None,
                'user': user
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Erro interno. Tente novamente.',
                'user': None
            }
    
    @staticmethod
    def resend_verification_code(email):
        """
        Resend verification code for an email.
        
        Args:
            email: Email address
            
        Returns:
            dict: Result with success status
        """
        try:
            # Find user by email
            from .models import User
            user = User.objects.filter(email=email).first()
            
            if not user:
                return {
                    'success': False,
                    'error': 'Email não encontrado'
                }
            
            if user.email_verified:
                return {
                    'success': False,
                    'error': 'Email já verificado'
                }
            
            # Create new verification code
            verification = EmailVerificationService.create_verification_code(user, email)
            
            # Send email
            if EmailVerificationService.send_verification_email(verification):
                return {
                    'success': True,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'error': 'Erro ao enviar email'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': 'Erro interno. Tente novamente.'
            }
    
    @staticmethod
    def send_welcome_email(user):
        """
        Send welcome email to user after successful verification.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            subject = '🎉 Bem-vindo(a) ao Tuwi!'
            
            # Create email context
            context = {
                'user_name': user.name,
                'user_email': user.email,
                'platform_url': f"{settings.FRONTEND_URL}/braiders",
                'profile_url': f"{settings.FRONTEND_URL}/profile",
                'current_year': timezone.now().year,
                'frontend_url': settings.FRONTEND_URL,
            }
            
            # Render HTML template
            html_message = render_to_string('emails/welcome_email.html', context)
            # Create plain text version
            text_message = strip_tags(html_message)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_message, "text/html")
            
            # Send email
            msg.send()
            
            return True
            
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            return False