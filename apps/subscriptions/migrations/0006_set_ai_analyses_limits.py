# Data migration to set default AI analyses limits for existing plans

from django.db import migrations


def set_ai_analyses_limits(apps, schema_editor):
    """
    Set default AI analyses limits:
    - FREE: 5 analyses per day
    - PREMIUM: 20 analyses per day
    - PREMIUM_PLUS: Unlimited (null)
    """
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')

    # Update FREE plan
    SubscriptionPlan.objects.filter(plan_type='FREE').update(daily_ai_analyses_limit=5)

    # Update PREMIUM plan
    SubscriptionPlan.objects.filter(plan_type='PREMIUM').update(daily_ai_analyses_limit=20)

    # PREMIUM_PLUS stays null (unlimited) - no action needed


def reverse_ai_analyses_limits(apps, schema_editor):
    """Reverse the limits (set all to null)"""
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    SubscriptionPlan.objects.all().update(daily_ai_analyses_limit=None)


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0005_add_daily_ai_analyses_limit'),
    ]

    operations = [
        migrations.RunPython(set_ai_analyses_limits, reverse_ai_analyses_limits),
    ]
