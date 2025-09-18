"""
Subscription Models - Sistema de assinaturas e planos

Este módulo define modelos para gerenciar assinaturas mensais,
planos (Free, Premium, Premium+) e limitações por tipo de usuário.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone


def get_current_date():
    """Helper function to get current date for default values"""
    return timezone.now().date()


class SubscriptionPlan(models.Model):
    """
    Plano de Assinatura - Define os diferentes tipos de planos disponíveis
    
    Exemplos: Free, Premium, Premium+
    """
    
    PLAN_TYPES = [
        ('FREE', 'Gratuito'),
        ('PREMIUM', 'Premium'),
        ('PREMIUM_PLUS', 'Premium Plus'),
    ]
    
    BILLING_CYCLES = [
        ('MONTHLY', 'Mensal'),
        ('YEARLY', 'Anual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    description = models.TextField()
    
    # Preços em Kuanzas (AOA)
    monthly_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Preço mensal em Kuanzas (AOA)"
    )
    yearly_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Preço anual em Kuanzas (AOA) - com desconto"
    )
    
    # Limitações do plano
    daily_lessons_limit = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Limite diário de lições (null = ilimitado)"
    )
    daily_speaking_minutes = models.IntegerField(
        null=True,
        blank=True, 
        help_text="Minutos diários de Speaking Practice (null = ilimitado)"
    )
    daily_listening_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minutos diários de Listening Practice (null = ilimitado)"
    )
    hearts_limit = models.IntegerField(
        default=5,
        help_text="Número máximo de vidas (0 = ilimitado)"
    )
    hearts_recharge_hours = models.IntegerField(
        default=4,
        help_text="Horas para recarregar 1 vida (0 = sem recarga)"
    )
    
    # Recursos premium
    offline_downloads = models.BooleanField(default=False)
    certificates = models.BooleanField(default=False)
    ai_tutor = models.BooleanField(default=False)
    native_teacher_sessions = models.IntegerField(
        default=0,
        help_text="Sessões mensais com professores nativos"
    )
    advanced_analytics = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    streak_freeze = models.IntegerField(
        default=0,
        help_text="Freezes de streak por semana"
    )
    multiple_devices = models.IntegerField(
        default=1,
        help_text="Número de dispositivos simultâneos permitidos"
    )
    
    # Configurações
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'monthly_price']
    
    def __str__(self):
        return f"{self.name} - {self.monthly_price} Kz/mês"
    
    def get_yearly_discount_percentage(self):
        """Calcula percentual de desconto anual"""
        if self.yearly_price and self.monthly_price:
            yearly_equivalent = self.monthly_price * 12
            discount = yearly_equivalent - self.yearly_price
            return round((discount / yearly_equivalent) * 100, 1)
        return 0


class UserSubscription(models.Model):
    """
    Assinatura do Usuário - Controla a assinatura ativa de cada usuário
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Ativa'),
        ('CANCELED', 'Cancelada'),
        ('EXPIRED', 'Expirada'),
        ('PENDING', 'Pendente'),
        ('TRIAL', 'Período de Teste'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Datas de controle
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Pagamento
    stripe_subscription_id = models.CharField(max_length=200, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=200, null=True, blank=True)
    last_payment_at = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    # Controle de uso diário  
    last_reset_date = models.DateField(default=get_current_date)
    daily_lessons_used = models.IntegerField(default=0)
    daily_speaking_minutes_used = models.IntegerField(default=0)
    daily_listening_minutes_used = models.IntegerField(default=0)
    
    # Sistema de vidas
    current_hearts = models.IntegerField(default=5)
    last_heart_recharge = models.DateTimeField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_active(self):
        """Verifica se a assinatura está ativa"""
        now = timezone.now()
        return (
            self.status == 'ACTIVE' and 
            self.expires_at > now
        )
    
    def is_trial(self):
        """Verifica se está em período de teste"""
        now = timezone.now()
        return (
            self.status == 'TRIAL' and 
            self.trial_ends_at and 
            self.trial_ends_at > now
        )
    
    def days_until_expiry(self):
        """Dias até expirar"""
        now = timezone.now()
        if self.expires_at > now:
            return (self.expires_at - now).days
        return 0
    
    def reset_daily_usage_if_needed(self):
        """Reseta contadores diários se necessário"""
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.daily_lessons_used = 0
            self.daily_speaking_minutes_used = 0
            self.daily_listening_minutes_used = 0
            self.last_reset_date = today
            self.save(update_fields=[
                'daily_lessons_used', 
                'daily_speaking_minutes_used',
                'daily_listening_minutes_used',
                'last_reset_date'
            ])
    
    def can_take_lesson(self):
        """Verifica se pode fazer mais uma lição hoje"""
        self.reset_daily_usage_if_needed()
        
        if not self.plan.daily_lessons_limit:  # Ilimitado
            return True
            
        return self.daily_lessons_used < self.plan.daily_lessons_limit
    
    def can_use_speaking(self, minutes_needed=1):
        """Verifica se pode usar Speaking Practice"""
        self.reset_daily_usage_if_needed()
        
        if not self.plan.daily_speaking_minutes:  # Ilimitado
            return True
            
        return (self.daily_speaking_minutes_used + minutes_needed) <= self.plan.daily_speaking_minutes
    
    def can_use_listening(self, minutes_needed=1):
        """Verifica se pode usar Listening Practice"""
        self.reset_daily_usage_if_needed()
        
        if not self.plan.daily_listening_minutes:  # Ilimitado
            return True
            
        return (self.daily_listening_minutes_used + minutes_needed) <= self.plan.daily_listening_minutes
    
    def use_heart(self):
        """Usa uma vida"""
        if self.current_hearts > 0:
            self.current_hearts -= 1
            self.save(update_fields=['current_hearts'])
            return True
        return False
    
    def recharge_hearts_if_needed(self):
        """Recarrega vidas se necessário"""
        if self.plan.hearts_limit == 0:  # Vidas ilimitadas
            self.current_hearts = 999
            self.save(update_fields=['current_hearts'])
            return
            
        if self.current_hearts >= self.plan.hearts_limit:
            return  # Já está no máximo
            
        now = timezone.now()
        hours_since_recharge = (now - self.last_heart_recharge).total_seconds() / 3600
        hearts_to_add = int(hours_since_recharge / self.plan.hearts_recharge_hours)
        
        if hearts_to_add > 0:
            self.current_hearts = min(
                self.current_hearts + hearts_to_add,
                self.plan.hearts_limit
            )
            self.last_heart_recharge = now
            self.save(update_fields=['current_hearts', 'last_heart_recharge'])


class SubscriptionHistory(models.Model):
    """
    Histórico de Assinaturas - Registra mudanças e eventos da assinatura
    """
    
    EVENT_TYPES = [
        ('CREATED', 'Criada'),
        ('UPGRADED', 'Upgrade'),
        ('DOWNGRADED', 'Downgrade'),
        ('RENEWED', 'Renovada'),
        ('CANCELED', 'Cancelada'),
        ('EXPIRED', 'Expirada'),
        ('TRIAL_STARTED', 'Trial Iniciado'),
        ('TRIAL_ENDED', 'Trial Finalizado'),
        ('PAYMENT_SUCCESS', 'Pagamento Realizado'),
        ('PAYMENT_FAILED', 'Falha no Pagamento'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='history'
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    previous_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    new_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor pago em Kuanzas (AOA)"
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.event_type} - {self.created_at.date()}"


class PromotionalCode(models.Model):
    """
    Códigos Promocionais - Para descontos e trials gratuitos
    """
    
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentual'),
        ('FIXED_AMOUNT', 'Valor Fixo'),
        ('FREE_TRIAL', 'Trial Gratuito'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Valor do desconto (% ou AOA)"
    )
    
    # Limitações
    max_uses = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    
    # Aplicabilidade
    applicable_plans = models.ManyToManyField(
        SubscriptionPlan,
        blank=True,
        help_text="Planos elegíveis (vazio = todos)"
    )
    first_time_users_only = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}"
    
    def is_valid(self):
        """Verifica se o código está válido"""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            self.current_uses < self.max_uses
        )


class PromoCodeUsage(models.Model):
    """
    Uso de Códigos Promocionais - Registra quando um código foi usado
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.ForeignKey(
        PromotionalCode,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_usages'
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='promo_usages'
    )
    
    discount_applied = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Desconto aplicado em AOA"
    )
    
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['promo_code', 'user']
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.promo_code.code}"