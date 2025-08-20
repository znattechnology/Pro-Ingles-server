"""
Views for payment system.
"""

from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from decimal import Decimal
import stripe
import logging

from .models import (
    PaymentMethod, PaymentAccount, Payment, PaymentSplit,
    Refund, Wallet, WalletTransaction, PaymentIntent
)
from .serializers import (
    PaymentMethodSerializer, PaymentAccountSerializer,
    PaymentListSerializer, PaymentDetailSerializer, PaymentCreateSerializer,
    PaymentSplitSerializer, RefundSerializer, RefundCreateSerializer,
    WalletSerializer, WalletTransactionSerializer,
    PaymentIntentSerializer, PaymentIntentCreateSerializer,
    PaymentStatsSerializer, StripeConnectSerializer, WebhookEventSerializer
)
from .services import StripeService, PaymentService
from apps.core.pagination import CustomPagination

logger = logging.getLogger(__name__)


class PaymentFilter(django_filters.FilterSet):
    """Advanced filtering for payments."""
    
    status = django_filters.MultipleChoiceFilter(choices=Payment.PAYMENT_STATUS)
    payment_type = django_filters.MultipleChoiceFilter(choices=Payment.PAYMENT_TYPES)
    amount_range = django_filters.RangeFilter(field_name='amount')
    date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    
    class Meta:
        model = Payment
        fields = []


class PaymentMethodListView(generics.ListCreateAPIView):
    """List and create payment methods."""
    
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-is_default', '-created_at']
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete payment method."""
    
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete by marking inactive."""
        instance.is_active = False
        instance.save()


class PaymentAccountListView(generics.ListCreateAPIView):
    """List and create payment accounts."""
    
    serializer_class = PaymentAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PaymentAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentAccountDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update payment account."""
    
    serializer_class = PaymentAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaymentAccount.objects.filter(user=self.request.user)


class PaymentListView(generics.ListAPIView):
    """List user's payments."""
    
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['created_at', 'processed_at', 'amount']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        ).select_related('payer', 'payee', 'payment_method', 'booking')


class PaymentDetailView(generics.RetrieveAPIView):
    """Retrieve detailed payment information."""
    
    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        ).select_related('payer', 'payee', 'payment_method', 'payment_account', 'booking')


class PaymentCreateView(generics.CreateAPIView):
    """Create new payment."""
    
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        
        # Create payment intent
        try:
            intent, stripe_intent = StripeService.create_payment_intent(
                amount=payment.amount,
                user=payment.payer,
                metadata={
                    'payment_id': str(payment.id),
                    'payment_type': payment.payment_type
                }
            )
            
            payment.intent = intent
            payment.save()
            
            return Response({
                'message': 'Payment created successfully',
                'payment_id': str(payment.id),
                'client_secret': intent.client_secret
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            payment.mark_as_failed(str(e))
            
            return Response({
                'error': 'Failed to create payment intent',
                'payment_id': str(payment.id)
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentIntentListView(generics.ListCreateAPIView):
    """List and create payment intents."""
    
    serializer_class = PaymentIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return PaymentIntent.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentIntentCreateSerializer
        return PaymentIntentSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get booking if provided
            booking = None
            booking_id = serializer.validated_data.get('booking_id')
            if booking_id:
                from apps.bookings.models import Booking
                booking = get_object_or_404(Booking, id=booking_id, client=request.user)
            
            # Create payment intent
            intent, stripe_intent = StripeService.create_payment_intent(
                amount=serializer.validated_data['amount'],
                currency=serializer.validated_data.get('currency', 'EUR'),
                user=request.user,
                booking=booking,
                metadata=serializer.validated_data.get('metadata', {})
            )
            
            return Response({
                'payment_intent': PaymentIntentSerializer(intent).data,
                'client_secret': intent.client_secret
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            return Response({
                'error': 'Failed to create payment intent'
            }, status=status.HTTP_400_BAD_REQUEST)


class RefundListView(generics.ListAPIView):
    """List user's refunds."""
    
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        user = self.request.user
        return Refund.objects.filter(
            payment__payer=user
        ).select_related('payment', 'initiated_by')


class RefundCreateView(generics.CreateAPIView):
    """Create refund for payment."""
    
    serializer_class = RefundCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        payment_id = self.kwargs['payment_id']
        context['payment'] = get_object_or_404(
            Payment, 
            id=payment_id,
            payer=self.request.user,
            status='succeeded'
        )
        return context
    
    def create(self, request, *args, **kwargs):
        payment = self.get_serializer_context()['payment']
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            refund = PaymentService.process_refund(
                payment=payment,
                amount=serializer.validated_data['amount'],
                reason=serializer.validated_data['reason'],
                initiated_by=request.user
            )
            
            return Response({
                'message': 'Refund processed successfully',
                'refund_id': str(refund.id)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class WalletView(generics.RetrieveAPIView):
    """Get user's wallet information."""
    
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class WalletTransactionListView(generics.ListAPIView):
    """List wallet transactions."""
    
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return WalletTransaction.objects.filter(wallet=wallet)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_connect_account(request):
    """Create Stripe Connect account for braider."""
    serializer = StripeConnectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        account, stripe_account = StripeService.create_connected_account(
            user=request.user,
            account_type=serializer.validated_data.get('account_type', 'express')
        )
        
        # Create account onboarding link
        refresh_url = request.build_absolute_uri('/payments/stripe/refresh/')
        return_url = request.build_absolute_uri('/payments/stripe/return/')
        
        account_link = StripeService.create_account_link(
            account_id=account.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url
        )
        
        return Response({
            'account_id': str(account.id),
            'stripe_account_id': account.stripe_account_id,
            'onboarding_url': account_link.url
        })
        
    except Exception as e:
        logger.error(f"Error creating Stripe Connect account: {str(e)}")
        return Response({
            'error': 'Failed to create Connect account'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_payment_intent(request, intent_id):
    """Confirm payment intent."""
    try:
        intent = get_object_or_404(
            PaymentIntent,
            external_intent_id=intent_id,
            user=request.user
        )
        
        payment_method_id = request.data.get('payment_method_id')
        
        stripe_intent = StripeService.confirm_payment_intent(
            intent_id=intent_id,
            payment_method_id=payment_method_id
        )
        
        # Update local intent
        intent.status = stripe_intent.status
        intent.save()
        
        return Response({
            'status': stripe_intent.status,
            'client_secret': stripe_intent.client_secret,
            'requires_action': stripe_intent.status == 'requires_action'
        })
        
    except Exception as e:
        logger.error(f"Error confirming payment intent: {str(e)}")
        return Response({
            'error': 'Failed to confirm payment intent'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_stats(request):
    """Get user's payment statistics."""
    try:
        stats = PaymentService.get_user_payment_stats(request.user)
        
        # Add wallet info
        try:
            wallet = Wallet.objects.get(user=request.user)
            stats['wallet_balance'] = wallet.available_balance
            stats['wallet_pending'] = wallet.pending_balance
        except Wallet.DoesNotExist:
            stats['wallet_balance'] = Decimal('0.00')
            stats['wallet_pending'] = Decimal('0.00')
        
        # Add monthly stats
        current_month = timezone.now().replace(day=1)
        monthly_paid = Payment.objects.filter(
            payer=request.user,
            status='succeeded',
            created_at__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_received = Payment.objects.filter(
            payee=request.user,
            status='succeeded',
            created_at__gte=current_month
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        
        stats['monthly_paid'] = monthly_paid
        stats['monthly_received'] = monthly_received
        
        serializer = PaymentStatsSerializer(stats)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting payment stats: {str(e)}")
        return Response({
            'error': 'Failed to get payment statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid Stripe webhook payload")
        return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature")
        return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            _handle_payment_success(payment_intent)
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            _handle_payment_failure(payment_intent)
            
        elif event['type'] == 'account.updated':
            account = event['data']['object']
            _handle_account_update(account)
            
        elif event['type'] == 'transfer.created':
            transfer = event['data']['object']
            _handle_transfer_created(transfer)
        
        logger.info(f"Handled Stripe webhook: {event['type']}")
        return Response({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {str(e)}")
        return Response({'error': 'Webhook processing failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _handle_payment_success(payment_intent):
    """Handle successful payment."""
    try:
        intent = PaymentIntent.objects.get(
            external_intent_id=payment_intent['id']
        )
        
        # Update intent status
        intent.status = 'succeeded'
        intent.save()
        
        # Update or create payment record
        if intent.payment:
            payment = intent.payment
            payment.mark_as_succeeded(
                external_id=payment_intent.get('latest_charge'),
                provider_response=payment_intent
            )
        else:
            # Create payment record if it doesn't exist
            payment = Payment.objects.create(
                payer=intent.user,
                amount=Decimal(str(payment_intent['amount'])) / 100,  # Convert from cents
                currency=payment_intent['currency'].upper(),
                payment_type='booking_payment',
                status='succeeded',
                processed_at=timezone.now(),
                external_id=payment_intent.get('latest_charge'),
                provider_response=payment_intent,
                booking=intent.booking,
                description=intent.description
            )
            intent.payment = payment
            intent.save()
        
        # Process payment splits
        if payment.payee:
            PaymentService.process_payment_splits(payment)
        
        # Send notification
        from apps.notifications.integrations import notify_system
        notify_system(
            payment.payer,
            "Pagamento Processado",
            f"Seu pagamento de €{payment.amount} foi processado com sucesso.",
            priority=3
        )
        
    except PaymentIntent.DoesNotExist:
        logger.warning(f"Payment intent not found: {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")


def _handle_payment_failure(payment_intent):
    """Handle failed payment."""
    try:
        intent = PaymentIntent.objects.get(
            external_intent_id=payment_intent['id']
        )
        
        intent.status = 'failed'
        intent.save()
        
        if intent.payment:
            intent.payment.mark_as_failed(
                reason=payment_intent.get('last_payment_error', {}).get('message', 'Payment failed'),
                code=payment_intent.get('last_payment_error', {}).get('code', '')
            )
        
        # Send notification
        from apps.notifications.integrations import notify_system
        notify_system(
            intent.user,
            "Falha no Pagamento",
            f"Houve um problema com o seu pagamento de €{intent.amount}. Por favor, tente novamente.",
            priority=3
        )
        
    except PaymentIntent.DoesNotExist:
        logger.warning(f"Payment intent not found: {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")


def _handle_account_update(account):
    """Handle Stripe account update."""
    try:
        payment_account = PaymentAccount.objects.get(
            stripe_account_id=account['id']
        )
        
        # Update account status based on Stripe data
        if account['charges_enabled'] and account['payouts_enabled']:
            payment_account.status = 'active'
            payment_account.can_receive_payments = True
            payment_account.can_instant_payout = account.get('capabilities', {}).get('transfers') == 'active'
        else:
            payment_account.status = 'restricted'
            payment_account.can_receive_payments = False
        
        payment_account.is_verified = account.get('details_submitted', False)
        payment_account.save()
        
    except PaymentAccount.DoesNotExist:
        logger.warning(f"Payment account not found: {account['id']}")
    except Exception as e:
        logger.error(f"Error handling account update: {str(e)}")


def _handle_transfer_created(transfer):
    """Handle transfer creation."""
    try:
        # Update payment split status if applicable
        split = PaymentSplit.objects.filter(
            transfer_id=transfer['id']
        ).first()
        
        if split:
            split.status = 'processed' if transfer['amount'] > 0 else 'failed'
            split.processed_at = timezone.now()
            split.save()
        
    except Exception as e:
        logger.error(f"Error handling transfer creation: {str(e)}")