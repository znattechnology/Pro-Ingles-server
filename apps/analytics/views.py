"""
Views for analytics and reporting system.
"""

from django.db.models import Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import FileResponse, Http404
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from datetime import timedelta
import logging

from .models import (
    MetricCategory, BusinessMetric, MetricDataPoint, Dashboard,
    DashboardWidget, Report, ReportGeneration, UserActivity,
    SystemPerformance, Alert, CohortAnalysis
)
from .serializers import (
    MetricCategorySerializer, BusinessMetricSerializer, MetricDataPointSerializer,
    DashboardSerializer, DashboardWidgetSerializer, ReportSerializer,
    ReportGenerationSerializer, UserActivitySerializer, SystemPerformanceSerializer,
    AlertSerializer, CohortAnalysisSerializer, KPIMetricsSerializer,
    FinancialMetricsSerializer, UserBehaviorMetricsSerializer,
    DashboardDataSerializer, WidgetDataSerializer, MetricDataCreateSerializer,
    AlertAcknowledgeSerializer, ReportGenerateSerializer
)
from .services import MetricsCalculator, DashboardService, AlertService
from .reports import generate_report, generate_executive_summary_pdf
from apps.core.pagination import CustomPagination

logger = logging.getLogger(__name__)


class MetricFilter(django_filters.FilterSet):
    """Advanced filtering for metrics."""
    
    category = django_filters.ModelChoiceFilter(queryset=MetricCategory.objects.all())
    metric_type = django_filters.MultipleChoiceFilter(choices=BusinessMetric.METRIC_TYPES)
    is_featured = django_filters.BooleanFilter()
    date_range = django_filters.DateFromToRangeFilter(field_name='data_points__date')
    
    class Meta:
        model = BusinessMetric
        fields = []


class MetricCategoryListView(generics.ListCreateAPIView):
    """List and create metric categories."""
    
    queryset = MetricCategory.objects.filter(is_active=True)
    serializer_class = MetricCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['order', 'name']


class MetricCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete metric category."""
    
    queryset = MetricCategory.objects.all()
    serializer_class = MetricCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class BusinessMetricListView(generics.ListCreateAPIView):
    """List and create business metrics."""
    
    queryset = BusinessMetric.objects.filter(is_active=True)
    serializer_class = BusinessMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MetricFilter
    search_fields = ['name', 'display_name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['category', 'name']
    pagination_class = CustomPagination


class BusinessMetricDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete business metric."""
    
    queryset = BusinessMetric.objects.all()
    serializer_class = BusinessMetricSerializer
    permission_classes = [permissions.IsAuthenticated]


class MetricDataPointListView(generics.ListCreateAPIView):
    """List and create metric data points."""
    
    serializer_class = MetricDataPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['metric', 'date']
    ordering = ['-timestamp']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        metric_id = self.kwargs.get('metric_id')
        if metric_id:
            return MetricDataPoint.objects.filter(metric_id=metric_id)
        return MetricDataPoint.objects.all()


class DashboardListView(generics.ListCreateAPIView):
    """List and create dashboards."""
    
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['dashboard_type', 'is_public']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Dashboard.objects.filter(is_active=True)
        
        if not user.is_staff:
            # Non-staff users can only see public dashboards or their assigned ones
            queryset = queryset.filter(
                Q(is_public=True) | Q(allowed_users=user)
            ).distinct()
        
        return queryset


class DashboardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete dashboard."""
    
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Dashboard.objects.filter(is_active=True)
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(allowed_users=user)
            ).distinct()
        
        return queryset


class ReportListView(generics.ListCreateAPIView):
    """List and create reports."""
    
    queryset = Report.objects.filter(is_active=True)
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report_type', 'schedule_type', 'output_format']
    ordering = ['-created_at']
    pagination_class = CustomPagination


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete report."""
    
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReportGenerationListView(generics.ListAPIView):
    """List report generations."""
    
    serializer_class = ReportGenerationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'report']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        report_id = self.kwargs.get('report_id')
        if report_id:
            return ReportGeneration.objects.filter(report_id=report_id)
        return ReportGeneration.objects.all()


class AlertListView(generics.ListAPIView):
    """List alerts."""
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'severity', 'alert_type']
    ordering = ['-created_at']
    pagination_class = CustomPagination


class AlertDetailView(generics.RetrieveAPIView):
    """Retrieve alert details."""
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def kpi_metrics(request):
    """Get KPI metrics."""
    try:
        # Get date range from query params
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        data = MetricsCalculator.calculate_kpi_metrics(start_date, end_date)
        serializer = KPIMetricsSerializer(data)
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting KPI metrics: {str(e)}")
        return Response(
            {'error': 'Failed to calculate KPI metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def financial_metrics(request):
    """Get financial metrics."""
    try:
        period = request.GET.get('period', 'month')
        data = MetricsCalculator.calculate_financial_metrics(period)
        serializer = FinancialMetricsSerializer(data)
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting financial metrics: {str(e)}")
        return Response(
            {'error': 'Failed to calculate financial metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_behavior_metrics(request):
    """Get user behavior metrics."""
    try:
        days = int(request.GET.get('days', 30))
        data = MetricsCalculator.calculate_user_behavior_metrics(days)
        serializer = UserBehaviorMetricsSerializer(data)
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting user behavior metrics: {str(e)}")
        return Response(
            {'error': 'Failed to calculate user behavior metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def executive_dashboard(request):
    """Get executive dashboard data."""
    try:
        data = DashboardService.get_executive_dashboard_data()
        serializer = DashboardDataSerializer(data)
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting executive dashboard data: {str(e)}")
        return Response(
            {'error': 'Failed to get dashboard data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def financial_dashboard(request):
    """Get financial dashboard data."""
    try:
        data = DashboardService.get_financial_dashboard_data()
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error getting financial dashboard data: {str(e)}")
        return Response(
            {'error': 'Failed to get financial dashboard data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_widgets(request, dashboard_id):
    """Get widgets for a dashboard."""
    try:
        widgets = DashboardService.get_dashboard_widgets(dashboard_id)
        
        return Response(widgets)
        
    except Exception as e:
        logger.error(f"Error getting dashboard widgets: {str(e)}")
        return Response(
            {'error': 'Failed to get dashboard widgets'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def store_metric_data(request):
    """Store metric data point."""
    serializer = MetricDataCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            MetricsCalculator.store_metric_datapoint(
                metric_name=serializer.validated_data['metric_name'],
                value=float(serializer.validated_data['value']),
                dimensions=serializer.validated_data.get('dimensions', {}),
                timestamp=serializer.validated_data.get('timestamp')
            )
            
            return Response({'message': 'Metric data stored successfully'})
            
        except Exception as e:
            logger.error(f"Error storing metric data: {str(e)}")
            return Response(
                {'error': 'Failed to store metric data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert."""
    try:
        alert = get_object_or_404(Alert, id=alert_id, status='active')
        
        serializer = AlertAcknowledgeSerializer(data=request.data)
        if serializer.is_valid():
            alert.acknowledge(request.user)
            
            return Response({'message': 'Alert acknowledged successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        return Response(
            {'error': 'Failed to acknowledge alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resolve_alert(request, alert_id):
    """Resolve an alert."""
    try:
        alert = get_object_or_404(Alert, id=alert_id, status__in=['active', 'acknowledged'])
        alert.resolve()
        
        return Response({'message': 'Alert resolved successfully'})
        
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        return Response(
            {'error': 'Failed to resolve alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_report_view(request, report_id):
    """Generate a report."""
    try:
        serializer = ReportGenerateSerializer(data=request.data)
        if serializer.is_valid():
            generation = generate_report(report_id, request.user)
            
            response_serializer = ReportGenerationSerializer(generation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_report(request, generation_id):
    """Download a generated report."""
    try:
        generation = get_object_or_404(ReportGeneration, id=generation_id, status='completed')
        
        if not generation.file_path:
            raise Http404("Report file not found")
        
        # Increment download count
        generation.download_count += 1
        generation.save(update_fields=['download_count'])
        
        # Return file
        response = FileResponse(
            open(generation.file_path, 'rb'),
            as_attachment=True,
            filename=f"{generation.report.name}_{generation.created_at.strftime('%Y%m%d')}.{generation.report.output_format}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise Http404("Report not found")


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_executive_summary(request):
    """Export executive summary as PDF."""
    try:
        file_path = generate_executive_summary_pdf()
        
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=f"executive_summary_{timezone.now().strftime('%Y%m%d')}.pdf"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting executive summary: {str(e)}")
        return Response(
            {'error': 'Failed to export executive summary'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def analytics_summary(request):
    """Get analytics summary for current user."""
    try:
        user = request.user
        
        # Get user's recent activities
        recent_activities = UserActivity.objects.filter(
            user=user
        ).order_by('-timestamp')[:10]
        
        # Get alerts for staff users
        alerts = []
        if user.is_staff:
            alerts = Alert.objects.filter(
                status='active'
            ).order_by('-created_at')[:5]
        
        # Get featured metrics
        featured_metrics = BusinessMetric.objects.filter(
            is_featured=True, is_active=True
        ).prefetch_related('data_points')[:5]
        
        # Build response
        data = {
            'recent_activities': UserActivitySerializer(recent_activities, many=True).data,
            'alerts': AlertSerializer(alerts, many=True).data if user.is_staff else [],
            'featured_metrics': BusinessMetricSerializer(featured_metrics, many=True).data,
            'dashboards_count': Dashboard.objects.filter(
                Q(is_public=True) | Q(allowed_users=user), is_active=True
            ).distinct().count(),
            'last_updated': timezone.now().isoformat()
        }
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {str(e)}")
        return Response(
            {'error': 'Failed to get analytics summary'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def track_user_activity(request):
    """Track user activity."""
    try:
        activity_type = request.data.get('activity_type')
        description = request.data.get('description', '')
        metadata = request.data.get('metadata', {})
        
        # Get user session info
        session_id = request.session.session_key
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        UserActivity.objects.create(
            user=request.user,
            activity_type=activity_type,
            description=description,
            metadata=metadata,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return Response({'message': 'Activity tracked successfully'})
        
    except Exception as e:
        logger.error(f"Error tracking user activity: {str(e)}")
        return Response(
            {'error': 'Failed to track activity'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def real_time_metrics(request):
    """Get real-time metrics."""
    try:
        # Get metrics from the last hour
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        
        # Recent activities count
        recent_activities = UserActivity.objects.filter(
            timestamp__gte=hour_ago
        ).count()
        
        # Active users count (users with activity in last hour)
        active_users = UserActivity.objects.filter(
            timestamp__gte=hour_ago
        ).values('user').distinct().count()
        
        # Recent payments (if available)
        recent_payments = 0
        recent_revenue = 0
        try:
            from apps.payments.models import Payment
            recent_payments_qs = Payment.objects.filter(
                processed_at__gte=hour_ago,
                status='succeeded'
            )
            recent_payments = recent_payments_qs.count()
            recent_revenue = float(recent_payments_qs.aggregate(
                total=Sum('amount')
            )['total'] or 0)
        except:
            pass
        
        data = {
            'timestamp': now.isoformat(),
            'metrics': {
                'recent_activities': recent_activities,
                'active_users': active_users,
                'recent_payments': recent_payments,
                'recent_revenue': recent_revenue
            }
        }
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {str(e)}")
        return Response(
            {'error': 'Failed to get real-time metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )