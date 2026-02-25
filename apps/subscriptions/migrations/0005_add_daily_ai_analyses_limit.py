# Generated migration for daily AI analyses limit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0004_ensure_subscription_plans'),
    ]

    operations = [
        # Add daily_ai_analyses_limit to SubscriptionPlan
        migrations.AddField(
            model_name='subscriptionplan',
            name='daily_ai_analyses_limit',
            field=models.IntegerField(
                blank=True,
                help_text='Limite diário de análises AI de pronúncia (null = ilimitado)',
                null=True,
            ),
        ),
        # Add daily_ai_analyses_used counter to UserSubscription
        migrations.AddField(
            model_name='usersubscription',
            name='daily_ai_analyses_used',
            field=models.IntegerField(default=0),
        ),
    ]
