"""
User models for the ProEnglish platform.

Following Django best practices with AbstractUser and proper role management.
"""

import uuid
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from apps.core.models import BaseModel, Address
from .managers import UserManager


class User(AbstractUser):
    """
    Custom user model extending AbstractUser.
    
    Improvements over original schema:
    - Uses AbstractUser instead of extending User (cleaner approach)
    - Proper role management with choices
    - Better field organization
    """
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
    ]
    
    # Override id to use UUID
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Required fields
    email = models.EmailField(
        unique=True,
        help_text="User's email address - used for login"
    )
    name = models.CharField(
        max_length=255,
        help_text="User's full name"
    )
    
    # Optional profile fields
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text="User's phone number"
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        help_text="User's profile picture"
    )
    
    # Role and status
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        help_text="User's role in the system"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user should be treated as active."
    )
    
    # Email verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether the user's email has been verified"
    )
    email_verification_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Token for email verification"
    )
    
    # Password reset
    reset_password_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Token for password reset"
    )
    reset_password_expires = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the password reset token expires"
    )
    
    # OAuth fields
    google_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="Google OAuth user ID"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    
    # JSON fields for preferences (using JSONField is better than JSONB reference)
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="User preferences and settings"
    )
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    # Custom manager
    objects = UserManager()
    
    # Fix related_name conflicts
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='tuwi_users',
        related_query_name='tuwi_user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='tuwi_users',
        related_query_name='tuwi_user',
    )
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email_verified']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def save(self, *args, **kwargs):
        # Sempre definir username como email para evitar problemas
        if self.email:
            self.username = self.email
        super().save(*args, **kwargs)
    
    @property
    def is_teacher(self):
        """Check if user is a teacher."""
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        """Check if user is a student."""
        return self.role == 'student'
    
    @property
    def is_platform_admin(self):
        """Check if user is a platform admin."""
        return self.role == 'admin'
    
    def get_full_name(self):
        """Return the user's full name."""
        return self.name
    
    def get_short_name(self):
        """Return the user's short name."""
        return self.name.split()[0] if self.name else self.email


class UserAddress(BaseModel):
    """
    User addresses - improved approach vs storing in JSON field.
    
    Benefits:
    - Proper validation
    - Easier querying
    - Better normalization
    - Supports multiple addresses per user
    """
    
    ADDRESS_TYPES = [
        ('billing', 'Billing Address'),
        ('shipping', 'Shipping Address'),
        ('home', 'Home Address'),
        ('work', 'Work Address'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES,
        default='home'
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default address for this type"
    )
    
    class Meta:
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'
        db_table = 'user_addresses'
        unique_together = ['user', 'address_type', 'is_default']
        indexes = [
            models.Index(fields=['user', 'address_type']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.get_address_type_display()}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per type per user
        if self.is_default:
            UserAddress.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)


class NotificationSettings(BaseModel):
    """
    User notification preferences.
    
    Improvements over original:
    - Better field organization
    - More granular control
    - Proper defaults
    """
    
    DIGEST_FREQUENCY_CHOICES = [
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('never', 'Never'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )
    
    # Email notifications
    email_bookings = models.BooleanField(
        default=True,
        help_text="Receive email notifications for booking updates"
    )
    email_messages = models.BooleanField(
        default=True,
        help_text="Receive email notifications for new messages"
    )
    email_ratings = models.BooleanField(
        default=True,
        help_text="Receive email notifications for new ratings"
    )
    email_orders = models.BooleanField(
        default=True,
        help_text="Receive email notifications for order updates"
    )
    email_marketing = models.BooleanField(
        default=False,
        help_text="Receive marketing emails"
    )
    
    # Push notifications (for future mobile app)
    push_bookings = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_ratings = models.BooleanField(default=True)
    push_orders = models.BooleanField(default=True)
    
    # Digest settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=DIGEST_FREQUENCY_CHOICES,
        default='daily',
        help_text="How often to receive digest emails"
    )
    
    # Quiet hours
    quiet_hours_start = models.TimeField(
        blank=True,
        null=True,
        help_text="Start of quiet hours (no notifications)"
    )
    quiet_hours_end = models.TimeField(
        blank=True,
        null=True,
        help_text="End of quiet hours"
    )
    
    timezone = models.CharField(
        max_length=50,
        default='Europe/Lisbon',
        help_text="User's timezone for notification timing"
    )
    
    class Meta:
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'
        db_table = 'notification_settings'
    
    def __str__(self):
        return f"Notification settings for {self.user.name}"


class EmailVerification(BaseModel):
    """
    Email verification codes for new user registration.
    
    Stores verification codes that are sent to users' emails
    during registration to verify email ownership.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    code = models.CharField(
        max_length=6,
        help_text="6-digit verification code"
    )
    email = models.EmailField(
        help_text="Email address this verification is for"
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Whether this verification code has been used"
    )
    expires_at = models.DateTimeField(
        help_text="When this verification code expires"
    )
    attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of verification attempts"
    )
    max_attempts = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of attempts allowed"
    )
    
    class Meta:
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
        db_table = 'email_verifications'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['email']),
            models.Index(fields=['code']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Email verification for {self.email} - {self.code}"
    
    def is_expired(self):
        """Check if the verification code has expired."""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if the verification code is valid (not used, not expired, not max attempts)."""
        return (
            not self.is_used and 
            not self.is_expired() and 
            self.attempts < self.max_attempts
        )
    
    def increment_attempts(self):
        """Increment the number of attempts."""
        self.attempts += 1
        self.save(update_fields=['attempts'])