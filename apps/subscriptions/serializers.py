"""
Subscription Serializers - API data serialization

Este módulo fornece serializers DRF para o sistema de assinaturas,
lidando com serialização de dados para comunicação frontend-backend.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionHistory,
    PromotionalCode,
    PromoCodeUsage
)

User = get_user_model()


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer para Planos de Assinatura
    """
    yearly_discount_percentage = serializers.ReadOnlyField(source='get_yearly_discount_percentage')
    is_most_popular = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'name', 
            'plan_type',
            'description',
            'monthly_price',
            'yearly_price',
            'yearly_discount_percentage',
            'is_most_popular',
            'features',
            # Limitações
            'daily_lessons_limit',
            'daily_speaking_minutes',
            'daily_listening_minutes',
            'hearts_limit',
            'hearts_recharge_hours',
            # Recursos premium
            'offline_downloads',
            'certificates',
            'ai_tutor',
            'native_teacher_sessions',
            'advanced_analytics',
            'priority_support',
            'streak_freeze',
            'multiple_devices',
            'sort_order',
            'is_active'
        ]
        
    def get_is_most_popular(self, obj):
        """Marca o plano Premium como mais popular"""
        return obj.plan_type == 'PREMIUM'
    
    def get_features(self, obj):
        """Retorna lista de recursos baseado no plano"""
        features = []
        
        if obj.plan_type == 'FREE':
            features = [
                f"{obj.daily_lessons_limit} lições por dia",
                f"{obj.daily_speaking_minutes} min de Speaking/dia", 
                f"{obj.daily_listening_minutes} min de Listening/dia",
                f"{obj.hearts_limit} vidas",
                "1 curso básico",
                "Progresso básico"
            ]
        elif obj.plan_type == 'PREMIUM':
            features = [
                "Lições ILIMITADAS",
                "Speaking & Listening ILIMITADO",
                "Vidas infinitas",
                "TODOS os cursos",
                "Certificados oficiais",
                "Analytics detalhado",
                "Download offline",
                "Suporte por email",
                f"{obj.streak_freeze} freeze/semana"
            ]
        elif obj.plan_type == 'PREMIUM_PLUS':
            features = [
                "TUDO do Premium",
                "IA Personal Tutor",
                f"{obj.native_teacher_sessions} sessões com nativos/mês",
                "Correção avançada IA",
                "Suporte prioritário",
                "Acesso antecipado",
                f"{obj.multiple_devices} dispositivos simultâneos",
                f"{obj.streak_freeze} freezes/semana"
            ]
            
        return features


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer para Assinatura do Usuário
    """
    plan = SubscriptionPlanSerializer(read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    days_until_expiry = serializers.ReadOnlyField()
    is_active_subscription = serializers.ReadOnlyField(source='is_active')
    is_trial_subscription = serializers.ReadOnlyField(source='is_trial')
    
    # Usage stats
    daily_usage = serializers.SerializerMethodField()
    hearts_status = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id',
            'user_name',
            'user_email',
            'plan',
            'status',
            'started_at',
            'expires_at',
            'canceled_at',
            'trial_ends_at',
            'days_until_expiry',
            'is_active_subscription',
            'is_trial_subscription',
            'daily_usage',
            'hearts_status',
            'stripe_subscription_id',
            'last_payment_at',
            'next_billing_date'
        ]
        read_only_fields = [
            'id', 'started_at', 'stripe_subscription_id',
            'last_payment_at', 'next_billing_date'
        ]
    
    def get_daily_usage(self, obj):
        """Retorna uso diário atual"""
        obj.reset_daily_usage_if_needed()
        return {
            'lessons_used': obj.daily_lessons_used,
            'lessons_limit': obj.plan.daily_lessons_limit,
            'speaking_minutes_used': obj.daily_speaking_minutes_used,
            'speaking_limit': obj.plan.daily_speaking_minutes,
            'listening_minutes_used': obj.daily_listening_minutes_used,
            'listening_limit': obj.plan.daily_listening_minutes,
            'can_take_lesson': obj.can_take_lesson(),
            'can_use_speaking': obj.can_use_speaking(),
            'can_use_listening': obj.can_use_listening()
        }
    
    def get_hearts_status(self, obj):
        """Retorna status das vidas"""
        obj.recharge_hearts_if_needed()
        return {
            'current_hearts': obj.current_hearts,
            'max_hearts': obj.plan.hearts_limit,
            'is_unlimited': obj.plan.hearts_limit == 0,
            'next_recharge': obj.last_heart_recharge,
            'recharge_hours': obj.plan.hearts_recharge_hours
        }


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """
    Serializer para Histórico de Assinatura
    """
    user_name = serializers.CharField(source='subscription.user.username', read_only=True)
    previous_plan_name = serializers.CharField(source='previous_plan.name', read_only=True)
    new_plan_name = serializers.CharField(source='new_plan.name', read_only=True)
    
    class Meta:
        model = SubscriptionHistory
        fields = [
            'id',
            'user_name',
            'event_type',
            'previous_plan_name',
            'new_plan_name',
            'amount_paid',
            'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PromotionalCodeSerializer(serializers.ModelSerializer):
    """
    Serializer para Códigos Promocionais
    """
    applicable_plan_names = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()
    is_valid_now = serializers.ReadOnlyField(source='is_valid')
    
    class Meta:
        model = PromotionalCode
        fields = [
            'id',
            'code',
            'name', 
            'description',
            'discount_type',
            'discount_value',
            'max_uses',
            'current_uses',
            'usage_stats',
            'valid_from',
            'valid_until',
            'applicable_plan_names',
            'first_time_users_only',
            'is_active',
            'is_valid_now'
        ]
    
    def get_applicable_plan_names(self, obj):
        """Retorna nomes dos planos aplicáveis"""
        if not obj.applicable_plans.exists():
            return ["Todos os planos"]
        return [plan.name for plan in obj.applicable_plans.all()]
    
    def get_usage_stats(self, obj):
        """Retorna estatísticas de uso"""
        return {
            'used': obj.current_uses,
            'remaining': obj.max_uses - obj.current_uses,
            'usage_percentage': (obj.current_uses / obj.max_uses * 100) if obj.max_uses > 0 else 0
        }


class PromoCodeUsageSerializer(serializers.ModelSerializer):
    """
    Serializer para Uso de Código Promocional
    """
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    promo_code_name = serializers.CharField(source='promo_code.code', read_only=True)
    
    class Meta:
        model = PromoCodeUsage
        fields = [
            'id',
            'user_name',
            'user_email',
            'promo_code_name',
            'discount_applied',
            'used_at'
        ]
        read_only_fields = ['id', 'used_at']


# Serializers específicos para operações

class SubscriptionUpgradeSerializer(serializers.Serializer):
    """
    Serializer para upgrade/downgrade de plano
    """
    plan_id = serializers.UUIDField()
    billing_cycle = serializers.ChoiceField(choices=['MONTHLY', 'YEARLY'], default='MONTHLY')
    promo_code = serializers.CharField(required=False, allow_blank=True)
    
    # Validation moved to view to return proper 404 status code


class ApplyPromoCodeSerializer(serializers.Serializer):
    """
    Serializer para aplicar código promocional
    """
    promo_code = serializers.CharField(max_length=50)
    plan_id = serializers.UUIDField()
    
    def validate_promo_code(self, value):
        """Valida se o código promocional existe e é válido"""
        try:
            promo = PromotionalCode.objects.get(code=value.upper())
            if not promo.is_valid():
                raise serializers.ValidationError("Código promocional expirado ou esgotado.")
            return value.upper()
        except PromotionalCode.DoesNotExist:
            raise serializers.ValidationError("Código promocional não encontrado.")

    def validate(self, data):
        """Validação cruzada entre código e plano"""
        promo_code = data.get('promo_code')
        plan_id = data.get('plan_id')
        
        if promo_code and plan_id:
            try:
                promo = PromotionalCode.objects.get(code=promo_code)
                plan = SubscriptionPlan.objects.get(id=plan_id)
                
                # Verificar se o código é aplicável ao plano
                if promo.applicable_plans.exists() and plan not in promo.applicable_plans.all():
                    raise serializers.ValidationError({
                        'promo_code': 'Este código não é válido para o plano selecionado.'
                    })
                    
            except (PromotionalCode.DoesNotExist, SubscriptionPlan.DoesNotExist):
                pass  # Já validado acima
                
        return data


class SubscriptionStatsSerializer(serializers.Serializer):
    """
    Serializer para estatísticas de assinatura (admin dashboard)
    """
    total_subscribers = serializers.IntegerField()
    monthly_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    conversion_rate = serializers.FloatField()
    churn_rate = serializers.FloatField()
    free_users = serializers.IntegerField()
    premium_users = serializers.IntegerField()
    premium_plus_users = serializers.IntegerField()
    active_promo_codes = serializers.IntegerField()
    recent_subscriptions = UserSubscriptionSerializer(many=True)
    revenue_chart = serializers.DictField()  # Dados para gráfico de receita