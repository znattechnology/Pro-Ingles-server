"""
Celery tasks for analytics and reporting.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_scheduled_reports():
    """Generate all scheduled reports that are due."""
    try:
        from .models import Report
        from .reports import generate_report
        
        now = timezone.now()
        due_reports = Report.objects.filter(
            is_active=True,
            schedule_type__in=['daily', 'weekly', 'monthly', 'quarterly'],
            next_scheduled__lte=now
        )
        
        generated_count = 0
        
        for report in due_reports:
            try:
                # Generate the report
                generation = generate_report(str(report.id))
                
                if generation.status == 'completed':
                    # Send email if recipients are configured
                    if report.email_recipients:
                        send_report_email.delay(str(generation.id))
                    
                    # Update next scheduled time
                    report.last_generated = now
                    report.next_scheduled = calculate_next_schedule_time(report)
                    report.save(update_fields=['last_generated', 'next_scheduled'])
                    
                    generated_count += 1
                    logger.info(f"Generated scheduled report: {report.name}")
                
            except Exception as e:
                logger.error(f"Error generating report {report.name}: {str(e)}")
        
        logger.info(f"Generated {generated_count} scheduled reports")
        return generated_count
        
    except Exception as e:
        logger.error(f"Error in generate_scheduled_reports task: {str(e)}")
        return 0


@shared_task
def send_report_email(generation_id):
    """Send generated report via email."""
    try:
        from .models import ReportGeneration
        
        generation = ReportGeneration.objects.get(id=generation_id)
        
        if generation.status != 'completed' or not generation.file_path:
            logger.warning(f"Report generation {generation_id} not ready for email")
            return False
        
        # Prepare email
        subject = f"Relatório Tuwi Beauty: {generation.report.name}"
        message = f"""
        Olá,
        
        O relatório "{generation.report.name}" foi gerado automaticamente.
        
        Informações do relatório:
        - Tipo: {generation.report.get_report_type_display()}
        - Gerado em: {generation.completed_at.strftime('%d/%m/%Y às %H:%M')}
        - Tamanho do arquivo: {generation.file_size / 1024:.1f} KB
        
        O relatório está anexado a este email.
        
        Atenciosamente,
        Equipe Tuwi Beauty
        """
        
        # Create email
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=generation.report.email_recipients
        )
        
        # Attach report file
        try:
            with open(generation.file_path, 'rb') as file:
                filename = f"{generation.report.name}_{generation.created_at.strftime('%Y%m%d')}.{generation.report.output_format}"
                email.attach(filename, file.read())
        except FileNotFoundError:
            logger.error(f"Report file not found: {generation.file_path}")
            return False
        
        # Send email
        email.send()
        logger.info(f"Sent report email for generation {generation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending report email: {str(e)}")
        return False


@shared_task
def check_metric_alerts():
    """Check all metrics for alert conditions."""
    try:
        from .services import AlertService
        
        alerts_created = AlertService.check_metric_thresholds()
        logger.info(f"Alert check completed, created {alerts_created} new alerts")
        return alerts_created
        
    except Exception as e:
        logger.error(f"Error in check_metric_alerts task: {str(e)}")
        return 0


@shared_task
def cleanup_old_data():
    """Cleanup old analytics data to maintain performance."""
    try:
        from .models import MetricDataPoint, UserActivity, SystemPerformance
        
        # Keep data for 1 year, archive older data
        cutoff_date = timezone.now() - timedelta(days=365)
        
        # Archive old metric data points (keep aggregated data)
        old_data_points = MetricDataPoint.objects.filter(timestamp__lt=cutoff_date)
        archived_count = old_data_points.count()
        
        # For now, just delete old data. In production, you might want to archive it.
        old_data_points.delete()
        
        # Cleanup old user activities (keep 90 days)
        activity_cutoff = timezone.now() - timedelta(days=90)
        old_activities = UserActivity.objects.filter(timestamp__lt=activity_cutoff)
        activity_count = old_activities.count()
        old_activities.delete()
        
        # Cleanup old performance data (keep 30 days)
        perf_cutoff = timezone.now() - timedelta(days=30)
        old_performance = SystemPerformance.objects.filter(timestamp__lt=perf_cutoff)
        perf_count = old_performance.count()
        old_performance.delete()
        
        logger.info(f"Cleanup completed: {archived_count} data points, {activity_count} activities, {perf_count} performance records")
        return {
            'data_points': archived_count,
            'activities': activity_count,
            'performance': perf_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data task: {str(e)}")
        return {}


@shared_task
def calculate_cohort_analysis():
    """Calculate cohort analysis for user retention."""
    try:
        from .models import CohortAnalysis, UserActivity
        from apps.users.models import User
        from django.db.models import Count, Avg
        
        # Calculate cohorts for the last 12 months
        end_date = timezone.now().date()
        start_date = end_date.replace(day=1) - timedelta(days=11*30)  # Approximately 12 months
        
        current_month = start_date.replace(day=1)
        cohorts_created = 0
        
        while current_month <= end_date:
            # Get users who registered in this month
            next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            cohort_users = User.objects.filter(
                date_joined__date__gte=current_month,
                date_joined__date__lt=next_month
            )
            
            cohort_size = cohort_users.count()
            
            if cohort_size == 0:
                current_month = next_month
                continue
            
            # Calculate retention for each subsequent period
            analysis_month = next_month
            period_number = 1
            
            while analysis_month <= end_date:
                analysis_next_month = (analysis_month.replace(day=28) + timedelta(days=4)).replace(day=1)
                
                # Count users who were active in this analysis period
                active_users = cohort_users.filter(
                    activities__timestamp__date__gte=analysis_month,
                    activities__timestamp__date__lt=analysis_next_month
                ).distinct().count()
                
                # Calculate retention rate
                retention_rate = (active_users / cohort_size) * 100 if cohort_size > 0 else 0
                
                # Get revenue metrics for this cohort in this period
                cohort_revenue = 0
                try:
                    from apps.payments.models import Payment
                    cohort_payments = Payment.objects.filter(
                        user__in=cohort_users,
                        status='succeeded',
                        processed_at__date__gte=analysis_month,
                        processed_at__date__lt=analysis_next_month
                    )
                    cohort_revenue = sum(float(p.amount) for p in cohort_payments)
                except:
                    pass
                
                # Average revenue per user
                avg_revenue_per_user = cohort_revenue / cohort_size if cohort_size > 0 else 0
                
                # Create or update cohort analysis record
                CohortAnalysis.objects.update_or_create(
                    cohort_period=current_month,
                    analysis_period=analysis_month,
                    defaults={
                        'cohort_size': cohort_size,
                        'active_users': active_users,
                        'retention_rate': retention_rate,
                        'total_revenue': cohort_revenue,
                        'average_revenue_per_user': avg_revenue_per_user,
                        'period_number': period_number
                    }
                )
                
                cohorts_created += 1
                analysis_month = analysis_next_month
                period_number += 1
            
            current_month = next_month
        
        logger.info(f"Cohort analysis completed, created/updated {cohorts_created} records")
        return cohorts_created
        
    except Exception as e:
        logger.error(f"Error in calculate_cohort_analysis task: {str(e)}")
        return 0


@shared_task
def update_kpi_snapshots():
    """Update daily KPI snapshots for faster dashboard loading."""
    try:
        from .services import MetricsCalculator
        from .models import BusinessMetric, MetricDataPoint
        from decimal import Decimal
        
        # Calculate today's KPIs
        today = timezone.now().date()
        kpis = MetricsCalculator.calculate_kpi_metrics(today, today)
        
        snapshots_created = 0
        
        # Store key metrics as data points for trending
        key_metrics = [
            ('daily_active_users', kpis['users']['active_users']),
            ('daily_bookings', kpis['bookings']['total_bookings']),
            ('daily_revenue', kpis['financial']['total_revenue']),
            ('daily_new_users', kpis['users']['new_users']),
            ('booking_conversion_rate', kpis['bookings']['booking_conversion_rate']),
            ('average_booking_value', kpis['financial']['avg_booking_value']),
        ]
        
        for metric_name, value in key_metrics:
            try:
                # Get or create metric
                metric, created = BusinessMetric.objects.get_or_create(
                    name=metric_name,
                    defaults={
                        'display_name': metric_name.replace('_', ' ').title(),
                        'category_id': 1,  # Assume first category exists
                        'metric_type': 'gauge',
                    }
                )
                
                # Create data point for today (avoid duplicates)
                data_point, created = MetricDataPoint.objects.get_or_create(
                    metric=metric,
                    date=today,
                    defaults={
                        'value': Decimal(str(value)),
                        'timestamp': timezone.now()
                    }
                )
                
                if created:
                    snapshots_created += 1
                
            except Exception as e:
                logger.error(f"Error creating snapshot for {metric_name}: {str(e)}")
        
        logger.info(f"KPI snapshots updated, created {snapshots_created} new data points")
        return snapshots_created
        
    except Exception as e:
        logger.error(f"Error in update_kpi_snapshots task: {str(e)}")
        return 0


def calculate_next_schedule_time(report):
    """Calculate the next scheduled time for a report."""
    from dateutil.relativedelta import relativedelta
    
    now = timezone.now()
    
    if report.schedule_type == 'daily':
        next_time = now.replace(hour=report.schedule_time.hour, minute=report.schedule_time.minute, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(days=1)
    
    elif report.schedule_type == 'weekly':
        # Find next occurrence of the scheduled day
        days_ahead = report.schedule_day_of_week - now.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        next_time = now + timedelta(days=days_ahead)
        next_time = next_time.replace(hour=report.schedule_time.hour, minute=report.schedule_time.minute, second=0, microsecond=0)
    
    elif report.schedule_type == 'monthly':
        next_time = now.replace(day=report.schedule_day_of_month, hour=report.schedule_time.hour, minute=report.schedule_time.minute, second=0, microsecond=0)
        if next_time <= now:
            next_time += relativedelta(months=1)
    
    elif report.schedule_type == 'quarterly':
        # Find next quarter
        current_quarter = (now.month - 1) // 3
        next_quarter_month = (current_quarter + 1) * 3 + 1
        if next_quarter_month > 12:
            next_quarter_month = 1
            next_time = now.replace(year=now.year + 1, month=next_quarter_month, day=report.schedule_day_of_month)
        else:
            next_time = now.replace(month=next_quarter_month, day=report.schedule_day_of_month)
        next_time = next_time.replace(hour=report.schedule_time.hour, minute=report.schedule_time.minute, second=0, microsecond=0)
    
    else:
        return None
    
    return next_time