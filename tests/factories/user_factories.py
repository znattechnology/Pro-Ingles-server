"""
Factory classes for User-related models.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""
    
    class Meta:
        model = get_user_model()
        django_get_or_create = ('email',)
    
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    name = factory.Faker('name')
    role = 'student'  # Using valid role from ROLE_CHOICES
    is_active = True
    email_verified = True
    phone = '+351912345678'  # Valid phone format
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password after creation."""
        if not create:
            return
        
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class TeacherFactory(UserFactory):
    """Factory for creating Teacher users."""
    
    role = 'teacher'
    name = factory.Faker('name')
    
    email = factory.Sequence(lambda n: f'teacher{n}@proenglish.com')


class StudentFactory(UserFactory):
    """Factory for creating Student users."""
    
    role = 'student'
    name = factory.Faker('name')
    
    email = factory.Sequence(lambda n: f'student{n}@example.com')


class AdminFactory(UserFactory):
    """Factory for creating Admin users."""
    
    role = 'admin'
    is_staff = True
    is_superuser = True
    name = factory.Faker('name')
    
    email = factory.Sequence(lambda n: f'admin{n}@proenglish.com')