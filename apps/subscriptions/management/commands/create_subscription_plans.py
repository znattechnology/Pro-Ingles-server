"""
Comando Django para criar os planos de assinatura iniciais

Usage: python manage.py create_subscription_plans
"""

from django.core.management.base import BaseCommand
from apps.subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Cria os planos de assinatura iniciais (Free, Premium, Premium+)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove planos existentes antes de criar novos',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo planos existentes...'))
            SubscriptionPlan.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Planos removidos com sucesso!'))
        
        # Dados dos planos em Kuanzas (AOA)
        plans_data = [
            {
                'name': 'Gratuito',
                'plan_type': 'FREE',
                'description': 'Perfeito para começar. Acesso básico com limite diário de lições e prática de conversação IA.',
                'monthly_price': 0.00,
                'yearly_price': 0.00,
                'daily_lessons_limit': 3,
                'daily_speaking_minutes': 5,  # 5 min/dia de conversação VAPI
                'daily_listening_minutes': 5,
                'hearts_limit': 3,
                'hearts_recharge_hours': 4,
                'trial_days': 7,  # 7 dias de trial
                'trial_speaking_minutes': 5,  # 5 min durante trial
                'offline_downloads': False,
                'certificates': False,
                'ai_tutor': False,
                'native_teacher_sessions': 0,
                'advanced_analytics': False,
                'priority_support': False,
                'streak_freeze': 0,
                'multiple_devices': 1,
                'sort_order': 1,
            },
            {
                'name': 'Premium',
                'plan_type': 'PREMIUM',
                'description': 'Aprendizagem sem limites. Lições ilimitadas, certificados oficiais, e relatórios avançados.',
                'monthly_price': 14950.00,  # 14.950 Kz (~$18 USD)
                'yearly_price': 149500.00,  # 149.500 Kz (economia de ~17%)
                'daily_lessons_limit': None,  # Ilimitado
                'daily_speaking_minutes': 10,  # 10 min/dia de conversação VAPI
                'daily_listening_minutes': None,  # Ilimitado
                'hearts_limit': 0,  # Ilimitado
                'hearts_recharge_hours': 0,
                'trial_days': 0,
                'trial_speaking_minutes': 0,
                'offline_downloads': True,
                'certificates': True,
                'ai_tutor': False,
                'native_teacher_sessions': 0,
                'advanced_analytics': True,
                'priority_support': False,
                'streak_freeze': 1,
                'multiple_devices': 2,
                'sort_order': 2,
            },
            {
                'name': 'Premium Plus',
                'plan_type': 'PREMIUM_PLUS',
                'description': 'A experiência completa. Tudo do Premium + IA Professor pessoal e sessões com professores nativos.',
                'monthly_price': 24950.00,  # 24.950 Kz (~$30 USD)
                'yearly_price': 249500.00,  # 249.500 Kz (economia de ~17%)
                'daily_lessons_limit': None,  # Ilimitado
                'daily_speaking_minutes': 20,  # 20 min/dia de conversação VAPI
                'daily_listening_minutes': None,  # Ilimitado
                'hearts_limit': 0,  # Ilimitado
                'hearts_recharge_hours': 0,
                'trial_days': 0,
                'trial_speaking_minutes': 0,
                'offline_downloads': True,
                'certificates': True,
                'ai_tutor': True,
                'native_teacher_sessions': 2,  # 2 sessões por mês
                'advanced_analytics': True,
                'priority_support': True,
                'streak_freeze': 2,
                'multiple_devices': 3,
                'sort_order': 3,
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Plano "{plan.name}" criado com sucesso!')
                )
            else:
                # Atualizar campos se o plano já existe
                for field, value in plan_data.items():
                    if field != 'plan_type':  # Não atualizar a chave
                        setattr(plan, field, value)
                plan.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Plano "{plan.name}" atualizado!')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Processo concluído!\n'
                f'   • {created_count} planos criados\n'
                f'   • {updated_count} planos atualizados\n'
                f'   • Total de planos: {SubscriptionPlan.objects.count()}'
            )
        )
        
        # Exibir resumo dos planos
        self.stdout.write(self.style.HTTP_INFO('\n📋 Planos disponíveis:'))
        for plan in SubscriptionPlan.objects.all().order_by('sort_order'):
            price_display = f'{plan.monthly_price:,.0f} Kz/mês' if plan.monthly_price > 0 else 'GRATUITO'
            self.stdout.write(f'   • {plan.name} - {price_display}')
            
            # Mostrar limitações principais
            if plan.plan_type == 'FREE':
                self.stdout.write(f'     → {plan.daily_lessons_limit} lições/dia, {plan.hearts_limit} vidas')
            elif plan.plan_type == 'PREMIUM':
                self.stdout.write(f'     → Ilimitado, certificados, analytics')
            elif plan.plan_type == 'PREMIUM_PLUS':
                self.stdout.write(f'     → Ilimitado + IA Tutor + {plan.native_teacher_sessions} sessões/mês')