"""
Management command to create default FREE subscriptions for users who don't have any.

This fixes the subscription plan count mismatches by ensuring all users have a subscription record.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.subscriptions.models import SubscriptionPlan, UserSubscription

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default FREE subscriptions for users who don\'t have any subscription records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating subscriptions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                '🔍 Checking for users without subscription records...\n'
            )
        )
        
        # Get FREE plan
        try:
            free_plan = SubscriptionPlan.objects.get(plan_type='FREE')
        except SubscriptionPlan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '❌ FREE subscription plan not found. Run create_subscription_plans first.'
                )
            )
            return
        
        # Find users without any subscription
        users_with_subscriptions = UserSubscription.objects.values_list('user_id', flat=True).distinct()
        users_without_subscriptions = User.objects.exclude(id__in=users_with_subscriptions)
        
        count = users_without_subscriptions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '✅ All users already have subscription records!'
                )
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'📊 Found {count} users without subscription records'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '🏃 DRY RUN MODE - No subscriptions will be created\n'
                )
            )
            
            for user in users_without_subscriptions[:10]:  # Show first 10
                self.stdout.write(f'   • {user.email} (ID: {user.id})')
            
            if count > 10:
                self.stdout.write(f'   ... and {count - 10} more users')
            
            return
        
        # Create subscriptions
        created_count = 0
        expires_at = timezone.now() + timedelta(days=365)  # 1 year for free plan
        
        self.stdout.write(
            self.style.SUCCESS(
                '🔧 Creating FREE subscriptions...\n'
            )
        )
        
        subscriptions_to_create = []
        for user in users_without_subscriptions:
            subscriptions_to_create.append(
                UserSubscription(
                    user=user,
                    plan=free_plan,
                    status='ACTIVE',
                    billing_cycle='MONTHLY',
                    expires_at=expires_at,
                    current_hearts=free_plan.hearts_limit
                )
            )
            created_count += 1
        
        # Bulk create for efficiency
        UserSubscription.objects.bulk_create(subscriptions_to_create, batch_size=100)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully created {created_count} FREE subscriptions!\n'
                f'📊 Subscription plan counts should now be accurate.'
            )
        )
        
        # Show updated statistics
        total_users = User.objects.count()
        total_subscriptions = UserSubscription.objects.filter(status='ACTIVE').count()
        
        self.stdout.write(
            f'📈 Updated statistics:\n'
            f'   • Total users: {total_users}\n'
            f'   • Active subscriptions: {total_subscriptions}\n'
            f'   • Coverage: {total_subscriptions}/{total_users} users have subscriptions'
        )