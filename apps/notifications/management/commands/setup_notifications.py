"""
Django management command to set up default notification templates and channels.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.notifications.models import (
    NotificationTemplate, NotificationChannel, NotificationCategory
)


class Command(BaseCommand):
    help = 'Set up default notification templates, channels, and categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate existing templates and channels',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(
            self.style.SUCCESS('Setting up notification system...')
        )
        
        with transaction.atomic():
            self.create_categories()
            self.create_channels()
            self.create_templates()
        
        self.stdout.write(
            self.style.SUCCESS('Notification system setup completed!')
        )

    def create_categories(self):
        """Create default notification categories."""
        categories_data = [
            {
                'name': 'booking',
                'display_name': 'Agendamentos',
                'description': 'Notificações relacionadas a agendamentos',
                'icon': '📅',
                'color': '#007bff',
                'priority': 3,
            },
            {
                'name': 'chat',
                'display_name': 'Mensagens',
                'description': 'Notificações de chat e mensagens',
                'icon': '💬',
                'color': '#28a745',
                'priority': 2,
            },
            {
                'name': 'rating',
                'display_name': 'Avaliações',
                'description': 'Notificações de avaliações e reviews',
                'icon': '⭐',
                'color': '#ffc107',
                'priority': 1,
            },
            {
                'name': 'system',
                'display_name': 'Sistema',
                'description': 'Notificações do sistema',
                'icon': '🔔',
                'color': '#6c757d',
                'priority': 4,
                'is_system': True,
            },
            {
                'name': 'marketing',
                'display_name': 'Marketing',
                'description': 'Notificações promocionais e marketing',
                'icon': '📢',
                'color': '#e83e8c',
                'priority': 0,
            },
        ]
        
        for category_data in categories_data:
            category, created = NotificationCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            
            if created:
                self.stdout.write(f'✓ Created category: {category.display_name}')
            else:
                self.stdout.write(f'- Category already exists: {category.display_name}')

    def create_channels(self):
        """Create default notification channels."""
        channels_data = [
            {
                'name': 'email_default',
                'channel_type': 'email',
                'config': {
                    'from_email': 'noreply@tuwi.pt',
                    'reply_to': 'contact@tuwi.pt',
                },
                'rate_limit_per_minute': 60,
                'rate_limit_per_hour': 1000,
                'rate_limit_per_day': 10000,
            },
            {
                'name': 'push_default',
                'channel_type': 'push',
                'config': {
                    'fcm_server_key': '',  # To be configured
                    'priority': 'high',
                },
                'rate_limit_per_minute': 100,
                'rate_limit_per_hour': 2000,
                'rate_limit_per_day': 20000,
            },
            {
                'name': 'in_app_default',
                'channel_type': 'in_app',
                'config': {},
                'rate_limit_per_minute': 200,
                'rate_limit_per_hour': 5000,
                'rate_limit_per_day': 50000,
            },
            {
                'name': 'sms_default',
                'channel_type': 'sms',
                'config': {
                    'provider': 'twilio',  # To be configured
                    'from_number': '',
                },
                'rate_limit_per_minute': 10,
                'rate_limit_per_hour': 100,
                'rate_limit_per_day': 500,
            },
        ]
        
        for channel_data in channels_data:
            channel, created = NotificationChannel.objects.get_or_create(
                name=channel_data['name'],
                defaults=channel_data
            )
            
            if created:
                self.stdout.write(f'✓ Created channel: {channel.name} ({channel.get_channel_type_display()})')
            else:
                self.stdout.write(f'- Channel already exists: {channel.name}')

    def create_templates(self):
        """Create default notification templates."""
        templates_data = [
            # Booking Templates
            {
                'name': 'booking_confirmation',
                'template_type': 'email',
                'subject_template': 'Agendamento Confirmado - Tuwi Beauty',
                'body_template': '''
Olá {{ user.first_name|default:user.email }}!

O seu agendamento foi confirmado com sucesso:

Detalhes do Agendamento:
- Serviço: {{ booking.service_name }}
- Data: {{ booking.scheduled_date|date:"d/m/Y" }}
- Hora: {{ booking.scheduled_time|time:"H:i" }}
- Braider: {{ booking.braider.user.get_full_name }}
- Localização: {{ booking.address }}

Valor: €{{ booking.total_price }}

Em caso de dúvidas, entre em contato conosco.

Obrigado por escolher a Tuwi Beauty!
                ''',
                'html_template': '''
<h2>Agendamento Confirmado</h2>
<p>Olá {{ user.first_name|default:user.email }}!</p>
<p>O seu agendamento foi confirmado com sucesso:</p>

<div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
    <h3>Detalhes do Agendamento:</h3>
    <ul>
        <li><strong>Serviço:</strong> {{ booking.service_name }}</li>
        <li><strong>Data:</strong> {{ booking.scheduled_date|date:"d/m/Y" }}</li>
        <li><strong>Hora:</strong> {{ booking.scheduled_time|time:"H:i" }}</li>
        <li><strong>Braider:</strong> {{ booking.braider.user.get_full_name }}</li>
        <li><strong>Localização:</strong> {{ booking.address }}</li>
    </ul>
    <p><strong>Valor: €{{ booking.total_price }}</strong></p>
</div>

<p>Em caso de dúvidas, entre em contato conosco.</p>
<p><strong>Obrigado por escolher a Tuwi Beauty!</strong></p>
                ''',
                'variables': {
                    'user': 'User object',
                    'booking': 'Booking object with details',
                },
                'description': 'Template para confirmação de agendamento',
            },
            {
                'name': 'booking_reminder',
                'template_type': 'push',
                'subject_template': 'Lembrete: Agendamento amanhã',
                'body_template': 'Seu agendamento com {{ booking.braider.user.get_full_name }} é amanhã às {{ booking.scheduled_time|time:"H:i" }}.',
                'variables': {
                    'booking': 'Booking object',
                },
                'description': 'Lembrete de agendamento para o dia seguinte',
            },
            
            # Chat Templates
            {
                'name': 'new_message',
                'template_type': 'push',
                'subject_template': 'Nova mensagem de {{ sender_name }}',
                'body_template': '{{ message_preview }}',
                'variables': {
                    'sender_name': 'Name of message sender',
                    'message_preview': 'Preview of message content',
                },
                'description': 'Notificação para nova mensagem no chat',
            },
            
            # Rating Templates
            {
                'name': 'new_rating',
                'template_type': 'email',
                'subject_template': 'Nova Avaliação Recebida - {{ stars }} estrelas',
                'body_template': '''
Olá {{ user.first_name|default:user.email }}!

Você recebeu uma nova avaliação de {{ stars }} estrelas!

{% if comment %}
Comentário: "{{ comment }}"
{% endif %}

Continue oferecendo um excelente serviço!

Equipe Tuwi Beauty
                ''',
                'variables': {
                    'user': 'Braider user object',
                    'stars': 'Rating stars (1-5)',
                    'comment': 'Optional rating comment',
                },
                'description': 'Notificação para braider sobre nova avaliação',
            },
            
            # System Templates
            {
                'name': 'welcome',
                'template_type': 'email',
                'subject_template': 'Bem-vindo à Tuwi Beauty!',
                'body_template': '''
Olá {{ user.first_name|default:user.email }}!

Bem-vindo à plataforma Tuwi Beauty!

Agora você pode:
- Agendar serviços com as melhores braiders
- Conversar diretamente com os profissionais
- Avaliar e ser avaliado
- Gerenciar seus agendamentos

Comece explorando nossa plataforma!

Equipe Tuwi Beauty
                ''',
                'html_template': '''
<h2>Bem-vindo à Tuwi Beauty!</h2>
<p>Olá {{ user.first_name|default:user.email }}!</p>
<p>Bem-vindo à plataforma Tuwi Beauty!</p>

<div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
    <h3>Agora você pode:</h3>
    <ul>
        <li>Agendar serviços com as melhores braiders</li>
        <li>Conversar diretamente com os profissionais</li>
        <li>Avaliar e ser avaliado</li>
        <li>Gerenciar seus agendamentos</li>
    </ul>
</div>

<p><strong>Comece explorando nossa plataforma!</strong></p>
<p>Equipe Tuwi Beauty</p>
                ''',
                'variables': {
                    'user': 'New user object',
                },
                'description': 'Email de boas-vindas para novos usuários',
            },
        ]
        
        for template_data in templates_data:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            
            if created:
                self.stdout.write(f'✓ Created template: {template.name} ({template.get_template_type_display()})')
            else:
                self.stdout.write(f'- Template already exists: {template.name}')
        
        self.stdout.write(
            self.style.WARNING(
                '\nNote: Remember to configure API keys for push notifications and SMS in the channel configs.'
            )
        )