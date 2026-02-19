"""
Subscription Models - Sistema de assinaturas e planos

Este módulo define modelos para gerenciar assinaturas mensais,
planos (Free, Premium, Premium+) e limitações por tipo de usuário.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F
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
    daily_ai_analyses_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Limite diário de análises AI de pronúncia (null = ilimitado)"
    )
    hearts_limit = models.IntegerField(
        default=5,
        help_text="Número máximo de vidas (0 = ilimitado)"
    )
    hearts_recharge_hours = models.IntegerField(
        default=4,
        help_text="Horas para recarregar 1 vida (0 = sem recarga)"
    )
    
    # Trial settings (para novos usuários)
    trial_days = models.IntegerField(
        default=0,
        help_text="Dias de trial após cadastro (0 = sem trial)"
    )
    trial_speaking_minutes = models.IntegerField(
        default=0,
        help_text="Minutos diários de speaking durante o trial"
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
    daily_ai_analyses_used = models.IntegerField(default=0)

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
        """
        Verifica se a assinatura está ativa.

        Uma assinatura é considerada ativa se:
        - Status é ACTIVE e não expirou
        - Status é CANCELED mas ainda não expirou (acesso até o fim do período pago)
        - Está em período de trial (baseado na data de criação do usuário)

        Nota: O status 'TRIAL' está deprecado. Agora usamos is_in_trial_period()
        para verificar trial de forma consistente.
        """
        now = timezone.now()

        # Verificar trial primeiro (baseado na data de criação do usuário)
        if self.is_in_trial_period():
            return True

        # Assinaturas ativas (inclui status TRIAL por compatibilidade)
        if self.status in ('ACTIVE', 'TRIAL') and self.expires_at > now:
            return True

        # Assinaturas canceladas mas ainda dentro do período pago
        if self.status == 'CANCELED' and self.expires_at > now:
            return True

        return False
    
    def is_trial(self):
        """
        Verifica se está em período de teste.

        UNIFIED: Agora usa is_in_trial_period() baseado na data de criação
        do usuário, que é mais preciso e consistente.

        O status 'TRIAL' e trial_ends_at estão deprecados - use is_in_trial_period().
        """
        return self.is_in_trial_period()
    
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
            self.daily_ai_analyses_used = 0
            self.last_reset_date = today
            self.save(update_fields=[
                'daily_lessons_used',
                'daily_speaking_minutes_used',
                'daily_listening_minutes_used',
                'daily_ai_analyses_used',
                'last_reset_date'
            ])
    
    def can_take_lesson(self):
        """Verifica se pode fazer mais uma lição hoje"""
        self.reset_daily_usage_if_needed()
        
        if not self.plan.daily_lessons_limit:  # Ilimitado
            return True
            
        return self.daily_lessons_used < self.plan.daily_lessons_limit
    
    def is_in_trial_period(self):
        """
        Verifica se o usuário está no período de trial.
        O trial é baseado na data de criação do usuário (created_at).
        """
        if not self.plan.trial_days or self.plan.trial_days <= 0:
            return False

        # Usar data de criação do usuário
        user_created = getattr(self.user, 'created_at', None) or getattr(self.user, 'date_joined', None)
        if not user_created:
            return False

        now = timezone.now()
        trial_end = user_created + timedelta(days=self.plan.trial_days)

        return now < trial_end

    def get_trial_remaining_days(self):
        """Retorna quantos dias restam do trial"""
        if not self.is_in_trial_period():
            return 0

        user_created = getattr(self.user, 'created_at', None) or getattr(self.user, 'date_joined', None)
        if not user_created:
            return 0

        now = timezone.now()
        trial_end = user_created + timedelta(days=self.plan.trial_days)
        remaining = (trial_end - now).days

        return max(0, remaining)

    def get_effective_speaking_limit(self):
        """
        Retorna o limite efetivo de speaking considerando trial.
        - Durante trial: usa trial_speaking_minutes
        - Após trial: usa daily_speaking_minutes (pode ser 0)
        """
        if self.is_in_trial_period() and self.plan.trial_speaking_minutes:
            return self.plan.trial_speaking_minutes
        return self.plan.daily_speaking_minutes or 0

    def can_use_speaking(self, minutes_needed=1):
        """
        Verifica se pode usar Speaking Practice.
        Considera período de trial para usuários no plano gratuito.
        """
        self.reset_daily_usage_if_needed()

        # Obter limite efetivo (considerando trial)
        effective_limit = self.get_effective_speaking_limit()

        # Limite null/None = ilimitado
        if effective_limit is None:
            return True

        # Limite 0 = bloqueado (plano gratuito após trial)
        if effective_limit == 0:
            return False

        return (self.daily_speaking_minutes_used + minutes_needed) <= effective_limit
    
    def can_use_listening(self, minutes_needed=1):
        """Verifica se pode usar Listening Practice"""
        self.reset_daily_usage_if_needed()

        if not self.plan.daily_listening_minutes:  # Ilimitado
            return True

        return (self.daily_listening_minutes_used + minutes_needed) <= self.plan.daily_listening_minutes

    def can_use_ai_analysis(self):
        """Verifica se pode usar análise AI de pronúncia"""
        self.reset_daily_usage_if_needed()

        if not self.plan.daily_ai_analyses_limit:  # Ilimitado (null)
            return True

        return self.daily_ai_analyses_used < self.plan.daily_ai_analyses_limit

    def get_ai_analyses_remaining(self):
        """Retorna quantas análises AI restam hoje"""
        self.reset_daily_usage_if_needed()

        if not self.plan.daily_ai_analyses_limit:  # Ilimitado
            return -1  # -1 indica ilimitado

        return max(0, self.plan.daily_ai_analyses_limit - self.daily_ai_analyses_used)

    @transaction.atomic
    def use_ai_analysis(self):
        """
        Usa uma análise AI de forma thread-safe.
        Retorna True se conseguiu usar, False se limite atingido.
        """
        self.reset_daily_usage_if_needed()

        if not self.plan.daily_ai_analyses_limit:  # Ilimitado
            self.daily_ai_analyses_used = F('daily_ai_analyses_used') + 1
            self.save(update_fields=['daily_ai_analyses_used'])
            self.refresh_from_db()
            return True

        # Lock the row for update to prevent race conditions
        locked_sub = UserSubscription.objects.select_for_update().get(pk=self.pk)

        if locked_sub.daily_ai_analyses_used < locked_sub.plan.daily_ai_analyses_limit:
            UserSubscription.objects.filter(pk=self.pk).update(
                daily_ai_analyses_used=F('daily_ai_analyses_used') + 1
            )
            self.refresh_from_db()
            return True

        return False

    @transaction.atomic
    def use_heart(self):
        """
        Usa uma vida de forma thread-safe.

        Uses select_for_update to prevent race conditions when multiple
        requests try to use hearts simultaneously.
        """
        # Lock the row for update to prevent race conditions
        locked_sub = UserSubscription.objects.select_for_update().get(pk=self.pk)

        if locked_sub.current_hearts > 0:
            # Use F() expression for atomic decrement
            UserSubscription.objects.filter(pk=self.pk).update(
                current_hearts=F('current_hearts') - 1
            )
            # Refresh to get updated value
            self.refresh_from_db()
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
    
    def has_hearts(self):
        """Verifica se o usuário tem vidas disponíveis"""
        self.recharge_hearts_if_needed()
        return self.current_hearts > 0


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