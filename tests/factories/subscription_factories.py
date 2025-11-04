"""
Factory classes for Subscription-related models.
"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal

from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from .user_factories import StudentFactory


class SubscriptionPlanFactory(DjangoModelFactory):
    """Factory for creating SubscriptionPlan instances."""
    
    class Meta:
        model = SubscriptionPlan
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['Free', 'Basic', 'Premium', 'Pro'])
    description = factory.Faker('paragraph', nb_sentences=2)
    price = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)
    duration_days = factory.Iterator([30, 90, 365])  # Monthly, quarterly, yearly
    max_courses = factory.Faker('random_int', min=1, max=100)
    max_practice_sessions = factory.Faker('random_int', min=10, max=1000)
    has_ai_features = factory.Iterator([True, False])
    has_offline_access = factory.Iterator([True, False])
    is_active = True
    
    @factory.lazy_attribute
    def features(self):
        """Generate features based on plan name."""
        base_features = ['Basic course access', 'Progress tracking']
        
        if self.name == 'Premium':
            base_features.extend(['AI pronunciation feedback', 'Unlimited practice'])
        elif self.name == 'Pro':
            base_features.extend(['AI pronunciation feedback', 'Unlimited practice', 
                                'Offline access', 'Personal tutor sessions'])
        
        return base_features


class FreePlanFactory(SubscriptionPlanFactory):
    """Factory for Free subscription plan."""
    
    name = 'Free'
    price = Decimal('0.00')
    max_courses = 3
    max_practice_sessions = 10
    has_ai_features = False
    has_offline_access = False


class BasicPlanFactory(SubscriptionPlanFactory):
    """Factory for Basic subscription plan."""
    
    name = 'Basic'
    price = Decimal('9.99')
    max_courses = 10
    max_practice_sessions = 100
    has_ai_features = False
    has_offline_access = False


class PremiumPlanFactory(SubscriptionPlanFactory):
    """Factory for Premium subscription plan."""
    
    name = 'Premium'
    price = Decimal('19.99')
    max_courses = 50
    max_practice_sessions = 500
    has_ai_features = True
    has_offline_access = False


class ProPlanFactory(SubscriptionPlanFactory):
    """Factory for Pro subscription plan."""
    
    name = 'Pro'
    price = Decimal('39.99')
    max_courses = 999  # Unlimited
    max_practice_sessions = 9999  # Unlimited
    has_ai_features = True
    has_offline_access = True


class UserSubscriptionFactory(DjangoModelFactory):
    """Factory for creating UserSubscription instances."""
    
    class Meta:
        model = UserSubscription
        django_get_or_create = ('user', 'plan')
    
    user = factory.SubFactory(StudentFactory)
    plan = factory.SubFactory(SubscriptionPlanFactory)
    start_date = factory.Faker('date_this_year')
    is_active = True
    auto_renew = True
    payment_method = factory.Iterator(['stripe', 'paypal', 'bank_transfer'])
    
    @factory.lazy_attribute
    def end_date(self):
        """Calculate end date based on plan duration."""
        from datetime import timedelta
        return self.start_date + timedelta(days=self.plan.duration_days)
    
    @factory.post_generation
    def usage_tracking(self, create, extracted, **kwargs):
        """Initialize usage tracking."""
        if create:
            self.courses_used = 0
            self.practice_sessions_used = 0
            self.save()


class ActiveSubscriptionFactory(UserSubscriptionFactory):
    """Factory for active subscriptions."""
    
    is_active = True
    start_date = factory.Faker('date_this_month')
    
    @factory.lazy_attribute
    def end_date(self):
        """End date in the future."""
        from datetime import timedelta, date
        return date.today() + timedelta(days=30)


class ExpiredSubscriptionFactory(UserSubscriptionFactory):
    """Factory for expired subscriptions."""
    
    is_active = False
    start_date = factory.Faker('date_between', start_date='-6M', end_date='-2M')
    
    @factory.lazy_attribute
    def end_date(self):
        """End date in the past."""
        from datetime import timedelta
        return self.start_date + timedelta(days=30)