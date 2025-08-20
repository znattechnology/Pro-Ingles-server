"""
Base models and mixins for the Tuwi platform.
"""

import uuid
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """Abstract base model with UUID primary key."""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract base model with created_at and updated_at fields."""
    
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the record was last updated"
    )
    
    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel):
    """Base model combining UUID and timestamp functionality."""
    
    class Meta:
        abstract = True


class Address(BaseModel):
    """Reusable address model for users, braiders, etc."""
    
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    district = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Portugal')
    
    # Optional fields for more detailed addresses
    building_number = models.CharField(max_length=20, blank=True)
    apartment = models.CharField(max_length=20, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    additional_info = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        
    def __str__(self):
        return f"{self.street}, {self.city}, {self.postal_code}"
    
    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.street]
        if self.building_number:
            parts[0] = f"{self.street} {self.building_number}"
        if self.apartment:
            parts.append(f"Apt {self.apartment}")
        if self.floor:
            parts.append(f"Floor {self.floor}")
        parts.extend([self.city, self.postal_code, self.country])
        return ", ".join(parts)