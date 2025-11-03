"""
Admin API Views for ProEnglish Platform Dashboard

Provides comprehensive admin endpoints for:
- Dashboard overview with aggregated stats
- User management and analytics  
- System health monitoring
- Platform statistics

All endpoints require admin role authentication.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
try:
    from apps.courses.models.core import Course
except ImportError:
    from apps.courses.models import Course

try:
    from apps.courses.models.enrollment import CourseEnrollment
except ImportError:
    CourseEnrollment = None
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def check_admin_permission(user):
    """Verificar se o utilizador tem permissões de admin"""
    if not user.is_authenticated:
        return False
    return user.role == 'admin' or user.is_superuser


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    """
    Endpoint principal do dashboard admin.
    Retorna dados agregados para o painel de controlo.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado. Apenas administradores podem aceder a esta funcionalidade.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Calcular estatísticas de utilizadores
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        student_users = User.objects.filter(role='student').count()
        teacher_users = User.objects.filter(role='teacher').count()
        admin_users = User.objects.filter(role='admin').count()
        verified_users = User.objects.filter(email_verified=True).count() if hasattr(User._meta.get_field('email_verified'), 'name') else 0

        # Calcular estatísticas de cursos
        total_courses = Course.objects.count()
        published_courses = Course.objects.filter(status='Published').count()
        draft_courses = Course.objects.filter(status='Draft').count()

        # Calcular crescimento (últimos 30 dias vs 30 dias anteriores)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        sixty_days_ago = timezone.now() - timedelta(days=60)
        
        users_last_30 = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        users_previous_30 = User.objects.filter(
            date_joined__gte=sixty_days_ago,
            date_joined__lt=thirty_days_ago
        ).count()
        
        growth_rate = 0
        if users_previous_30 > 0:
            growth_rate = ((users_last_30 - users_previous_30) / users_previous_30) * 100
        elif users_last_30 > 0:
            growth_rate = 100

        # Taxa de engajamento (utilizadores activos vs total)
        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0

        # Utilizadores recentes (últimos 10)
        recent_users = User.objects.filter(
            role='student'
        ).order_by('-date_joined')[:10].values(
            'id', 'name', 'email', 'role', 'is_active', 
            'date_joined', 'last_login'
        )

        # Top cursos (simulado por enquanto)
        top_courses = [
            {
                'id': '1',
                'title': 'Inglês Avançado para Negócios',
                'type': 'video',
                'students': 234,
                'revenue': 11700.00,  # em USD
                'teacher_name': 'Prof. Maria Santos'
            },
            {
                'id': '2',
                'title': 'Conversação Inglesa',
                'type': 'practice',
                'students': 189,
                'revenue': 9450.00,
                'teacher_name': 'Prof. João Silva'
            },
            {
                'id': '3',
                'title': 'TOEFL Preparação',
                'type': 'video',
                'students': 156,
                'revenue': 7800.00,
                'teacher_name': 'Prof. Ana Costa'
            }
        ]

        # Dados do gráfico de receita (últimos 6 meses - simulado)
        revenue_chart = [
            {'month': 'Jun', 'revenue': 8500.00},
            {'month': 'Jul', 'revenue': 9000.00},
            {'month': 'Ago', 'revenue': 9875.00},
            {'month': 'Set', 'revenue': 10125.00},
            {'month': 'Out', 'revenue': 11125.00},
            {'month': 'Nov', 'revenue': 11150.00}
        ]

        # Dados do gráfico de crescimento de utilizadores (últimos 6 meses)
        current_date = timezone.now()
        user_growth_chart = []
        months = ['Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov']
        
        for i, month in enumerate(months):
            month_start = current_date.replace(day=1) - timedelta(days=30 * (5 - i))
            month_end = month_start + timedelta(days=30)
            
            users_in_month = User.objects.filter(
                date_joined__gte=month_start,
                date_joined__lt=month_end
            ).count()
            
            user_growth_chart.append({
                'month': month,
                'users': users_in_month
            })

        # Receita estimada (simulada por enquanto)
        total_revenue = 57100.00  # USD
        monthly_revenue = 11150.00  # USD

        dashboard_data = {
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'student_users': student_users,
                'teacher_users': teacher_users,
                'admin_users': admin_users,
                'verified_users': verified_users,
                'total_courses': total_courses,
                'published_courses': published_courses,
                'draft_courses': draft_courses,
                'total_revenue': total_revenue,
                'monthly_revenue': monthly_revenue,
                'growth_rate': round(growth_rate, 1),
                'engagement_rate': round(engagement_rate, 1)
            },
            'recent_users': list(recent_users),
            'top_courses': top_courses,
            'revenue_chart': revenue_chart,
            'user_growth_chart': user_growth_chart
        }

        logger.info(f"Admin dashboard accessed by {request.user.email}")
        return Response(dashboard_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        return Response(
            {'error': 'Erro interno do servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    """
    Listar todos os utilizadores com paginação e filtros.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Parâmetros de query
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # máximo 100
        search = request.GET.get('search', '')
        role_filter = request.GET.get('role', 'all')
        status_filter = request.GET.get('status', 'all')

        # Construir queryset
        queryset = User.objects.all()

        # Aplicar filtros
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )
        
        if role_filter != 'all':
            queryset = queryset.filter(role=role_filter)
        
        if status_filter != 'all':
            is_active = status_filter == 'active'
            queryset = queryset.filter(is_active=is_active)

        # Contar total
        total = queryset.count()
        
        # Aplicar paginação
        offset = (page - 1) * limit
        users = queryset.order_by('-date_joined')[offset:offset + limit]

        # Serializar dados
        users_data = []
        for user in users:
            users_data.append({
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'phone': user.phone or '',
                'role': user.role,
                'is_active': user.is_active,
                'email_verified': getattr(user, 'email_verified', False),
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'avatar': None  # Implementar quando existir campo avatar
            })

        # Estatísticas gerais
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'student_users': User.objects.filter(role='student').count(),
            'teacher_users': User.objects.filter(role='teacher').count(),
            'admin_users': User.objects.filter(role='admin').count(),
            'verified_users': User.objects.filter(email_verified=True).count() if hasattr(User._meta.get_field('email_verified'), 'name') else 0
        }

        # Informações de paginação
        total_pages = (total + limit - 1) // limit
        pagination = {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }

        return Response({
            'users': users_data,
            'pagination': pagination,
            'stats': stats
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in admin users list: {str(e)}")
        return Response(
            {'error': 'Erro ao listar utilizadores'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    """
    Obter estatísticas detalhadas da plataforma.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        period = request.GET.get('period', '30d')
        
        # Estatísticas gerais
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'student_users': User.objects.filter(role='student').count(),
            'teacher_users': User.objects.filter(role='teacher').count(),
            'admin_users': User.objects.filter(role='admin').count(),
            'verified_users': User.objects.filter(email_verified=True).count() if hasattr(User._meta.get_field('email_verified'), 'name') else 0,
            'total_courses': Course.objects.count(),
            'published_courses': Course.objects.filter(status='Published').count(),
            'draft_courses': Course.objects.filter(status='Draft').count(),
            'total_revenue': 57100.00,  # Simulado
            'monthly_revenue': 11150.00,  # Simulado
            'growth_rate': 23.5,  # Simulado
            'engagement_rate': 78.3  # Simulado
        }

        return Response(stats, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in admin stats: {str(e)}")
        return Response(
            {'error': 'Erro ao obter estatísticas'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_system_health(request):
    """
    Verificar a saúde do sistema.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Dados simulados de saúde do sistema
        health_data = {
            'status': 'healthy',
            'uptime': 72.5,  # horas
            'memory_usage': 65.2,  # percentagem
            'disk_usage': 34.8,  # percentagem
            'active_users': User.objects.filter(is_active=True).count(),
            'response_time': 145.2  # millisegundos
        }

        return Response(health_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in system health: {str(e)}")
        return Response(
            {'error': 'Erro ao verificar saúde do sistema'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, user_id):
    """
    Obter detalhes de um utilizador específico.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        
        user_data = {
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'is_active': user.is_active,
            'email_verified': getattr(user, 'email_verified', False),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'avatar': None  # Implementar quando existir campo avatar
        }

        return Response({'user': user_data}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {'error': 'Utilizador não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in admin user detail: {str(e)}")
        return Response(
            {'error': 'Erro ao obter detalhes do utilizador'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_user_status(request, user_id):
    """
    Atualizar o status (ativo/inativo) de um utilizador.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        
        # Não permitir que admin desative a si próprio
        if user.id == request.user.id:
            return Response(
                {'error': 'Não pode alterar o seu próprio status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response(
                {'error': 'Campo is_active é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = bool(is_active)
        user.save()
        
        logger.info(f"User {user.email} status changed to {'active' if is_active else 'inactive'} by {request.user.email}")
        
        user_data = {
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'is_active': user.is_active,
            'email_verified': getattr(user, 'email_verified', False),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'avatar': None
        }

        return Response({
            'message': f'Status do utilizador alterado para {"ativo" if is_active else "inativo"}',
            'user': user_data
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {'error': 'Utilizador não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in admin user status: {str(e)}")
        return Response(
            {'error': 'Erro ao alterar status do utilizador'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_user_role(request, user_id):
    """
    Atualizar a role de um utilizador.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        
        # Não permitir que admin altere a própria role
        if user.id == request.user.id:
            return Response(
                {'error': 'Não pode alterar a sua própria role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_role = request.data.get('role')
        if not new_role:
            return Response(
                {'error': 'Campo role é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_role not in ['student', 'teacher', 'admin']:
            return Response(
                {'error': 'Role inválida. Use: student, teacher, ou admin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_role = user.role
        user.role = new_role
        user.save()
        
        logger.info(f"User {user.email} role changed from {old_role} to {new_role} by {request.user.email}")
        
        user_data = {
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'is_active': user.is_active,
            'email_verified': getattr(user, 'email_verified', False),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'avatar': None
        }

        return Response({
            'message': f'Role do utilizador alterada de {old_role} para {new_role}',
            'user': user_data
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {'error': 'Utilizador não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in admin user role: {str(e)}")
        return Response(
            {'error': 'Erro ao alterar role do utilizador'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_user_delete(request, user_id):
    """
    Eliminar um utilizador (apenas desativar, não eliminar completamente).
    Por razões de segurança e auditoria, apenas desativamos a conta.
    """
    if not check_admin_permission(request.user):
        return Response(
            {'error': 'Acesso negado'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        
        # Não permitir que admin elimine a si próprio
        if user.id == request.user.id:
            return Response(
                {'error': 'Não pode eliminar a sua própria conta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Por segurança, apenas desativamos a conta em vez de eliminar
        user.is_active = False
        user.save()
        
        logger.warning(f"User {user.email} account deactivated (soft delete) by {request.user.email}")
        
        return Response({
            'message': f'Conta do utilizador {user.name} foi desativada com sucesso',
            'user_id': str(user.id),
            'action': 'deactivated'
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {'error': 'Utilizador não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in admin user delete: {str(e)}")
        return Response(
            {'error': 'Erro ao eliminar utilizador'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )