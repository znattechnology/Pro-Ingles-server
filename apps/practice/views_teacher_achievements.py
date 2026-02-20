"""
Teacher Achievement Management Views

Endpoints for teachers to create, edit, and manage achievements/badges
for the gamification system.

All endpoints require IsAuthenticated + IsTeacher permissions.
"""

from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status as status_module
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Achievement, UserAchievement
from .serializers import AchievementSerializer
from .permissions import IsTeacher


# ============================================================================
# TEACHER ACHIEVEMENT CRUD VIEWS
# ============================================================================

class TeacherAchievementListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/practice/teacher/achievements/     - List all achievements
    POST /api/v1/practice/teacher/achievements/     - Create new achievement

    Teacher only endpoint for managing achievements.
    """
    queryset = Achievement.objects.all().order_by('category', 'order')
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'rarity', 'is_active']

    def get_queryset(self):
        """Filter achievements with additional stats"""
        queryset = super().get_queryset()

        # Add unlock count annotation
        queryset = queryset.annotate(
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['include_stats'] = True
        return context


class TeacherAchievementDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/practice/teacher/achievements/{id}/  - Get achievement details
    PUT    /api/v1/practice/teacher/achievements/{id}/  - Update achievement
    PATCH  /api/v1/practice/teacher/achievements/{id}/  - Partial update
    DELETE /api/v1/practice/teacher/achievements/{id}/  - Delete achievement

    Teacher only endpoint for managing specific achievements.
    """
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        """Add unlock count annotation"""
        return super().get_queryset().annotate(
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        )


# ============================================================================
# TEACHER ACHIEVEMENT STATISTICS & ACTIONS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def teacher_achievement_stats(request):
    """
    GET /api/v1/practice/teacher/achievements/stats/

    Get achievement statistics for teacher dashboard.
    """
    try:
        total_achievements = Achievement.objects.count()
        active_achievements = Achievement.objects.filter(is_active=True).count()
        inactive_achievements = total_achievements - active_achievements

        # Total unlocks across all achievements
        total_unlocked = UserAchievement.objects.filter(is_unlocked=True).count()

        # Achievements by category
        category_stats = Achievement.objects.values('category').annotate(
            count=models.Count('id'),
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        ).order_by('category')

        # Achievements by rarity
        rarity_stats = Achievement.objects.values('rarity').annotate(
            count=models.Count('id'),
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        ).order_by('rarity')

        # Recent unlocks (last 7 days)
        recent_date = timezone.now() - timedelta(days=7)
        recent_unlocks = UserAchievement.objects.filter(
            is_unlocked=True,
            unlocked_at__gte=recent_date
        ).count()

        return Response({
            'total_achievements': total_achievements,
            'active_achievements': active_achievements,
            'inactive_achievements': inactive_achievements,
            'total_unlocked': total_unlocked,
            'recent_unlocks': recent_unlocks,
            'category_breakdown': list(category_stats),
            'rarity_breakdown': list(rarity_stats)
        })

    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar estatísticas: {str(e)}'},
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def toggle_achievement_status(request, achievement_id):
    """
    POST /api/v1/practice/teacher/achievements/{id}/toggle-status/

    Toggle achievement active/inactive status.
    """
    try:
        achievement = get_object_or_404(Achievement, id=achievement_id)
        achievement.is_active = not achievement.is_active
        achievement.save()

        return Response({
            'message': f'Conquista {"ativada" if achievement.is_active else "desativada"} com sucesso',
            'is_active': achievement.is_active
        })

    except Exception as e:
        return Response(
            {'error': f'Erro ao alterar status: {str(e)}'},
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def bulk_update_achievements(request):
    """
    POST /api/v1/practice/teacher/achievements/bulk-update/

    Bulk update achievement properties (activate/deactivate multiple, reorder, delete).

    Request body:
    {
        "action": "activate" | "deactivate" | "delete" | "reorder",
        "achievement_ids": ["uuid1", "uuid2", ...],
        "order_data": [{"id": "uuid", "order": 1}, ...] (only for reorder action)
    }
    """
    try:
        action = request.data.get('action')
        achievement_ids = request.data.get('achievement_ids', [])

        if not action or not achievement_ids:
            return Response(
                {'error': 'Ação e IDs das conquistas são obrigatórios'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        achievements = Achievement.objects.filter(id__in=achievement_ids)

        if action == 'activate':
            achievements.update(is_active=True)
            message = f'{achievements.count()} conquistas ativadas'

        elif action == 'deactivate':
            achievements.update(is_active=False)
            message = f'{achievements.count()} conquistas desativadas'

        elif action == 'delete':
            count = achievements.count()
            achievements.delete()
            message = f'{count} conquistas removidas'

        elif action == 'reorder':
            # Update order based on provided order list
            order_data = request.data.get('order_data', [])
            for item in order_data:
                Achievement.objects.filter(id=item['id']).update(order=item['order'])
            message = 'Ordem das conquistas atualizada'

        else:
            return Response(
                {'error': 'Ação inválida. Use: activate, deactivate, delete, ou reorder'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        return Response({'message': message})

    except Exception as e:
        return Response(
            {'error': f'Erro na operação em lote: {str(e)}'},
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def achievement_unlock_analytics(request, achievement_id):
    """
    GET /api/v1/practice/teacher/achievements/{id}/analytics/

    Get detailed analytics for specific achievement (unlock trends, user stats, etc.).
    """
    try:
        achievement = get_object_or_404(Achievement, id=achievement_id)

        # Basic unlock stats
        total_unlocks = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=True
        ).count()

        # Unlock timeline (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        unlock_timeline = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=True,
            unlocked_at__gte=thirty_days_ago
        ).extra(
            select={'day': 'date(unlocked_at)'}
        ).values('day').annotate(
            count=models.Count('id')
        ).order_by('day')

        # Users in progress
        users_in_progress = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=False,
            current_progress__gt=0
        ).count()

        # Average progress for users who haven't unlocked yet
        avg_progress = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=False
        ).aggregate(
            avg_progress=models.Avg('current_progress')
        )

        return Response({
            'achievement': {
                'id': str(achievement.id),
                'title': achievement.title,
                'description': achievement.description,
                'category': achievement.category,
                'rarity': achievement.rarity,
                'requirement_target': achievement.requirement_target
            },
            'stats': {
                'total_unlocks': total_unlocks,
                'users_in_progress': users_in_progress,
                'average_progress': avg_progress['avg_progress'] or 0,
                'unlock_timeline': list(unlock_timeline)
            }
        })

    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar analytics: {str(e)}'},
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )
