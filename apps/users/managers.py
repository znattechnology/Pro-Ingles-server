"""
Custom managers for user models.
"""

from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model with email as username.
    """
    
    def create_user(self, email, name, password=None, **extra_fields):
        """
        Create and save a regular user with the given email, name and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        if name is None:
            raise ValueError('The Name field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        """
        Create and save a superuser with the given email, name and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, name, password, **extra_fields)
    
    
    def active_users(self):
        """
        Return only active users.
        """
        return self.filter(is_active=True)
    
    def verified_users(self):
        """
        Return only email-verified users.
        """
        return self.filter(email_verified=True)
    
    def customers(self):
        """
        Return only customer users.
        """
        return self.filter(role='customer')
    
    def braiders(self):
        """
        Return only braider users.
        """
        return self.filter(role='braider')
    
    def admins(self):
        """
        Return only admin users.
        """
        return self.filter(role='admin')