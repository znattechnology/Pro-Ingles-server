"""
Practice Course Management Views
Endpoints específicos para gerenciar practice courses (deletar e publicar/despublicar)
"""

import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class PracticeCourseManagementView(APIView):
    """
    DELETE /api/v1/practice/courses/{course_id}/
    PUT /api/v1/practice/courses/{course_id}/
    
    Gerenciamento específico de practice courses (deletar e publicar/despublicar)
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, course_id):
        """Get practice course and verify ownership"""
        try:
            from apps.courses.models import Course
            course = Course.objects.get(id=course_id, course_type='practice')
            
            # Verify if user is the teacher
            if course.teacher != self.request.user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Apenas o professor pode gerenciar este curso")
                
            return course
        except Course.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Practice course não encontrado")
    
    def delete(self, request, course_id):
        """Delete practice course"""
        course = self.get_object(course_id)
        
        logger.info(f"🗑️ Deleting practice course: {course.title} (ID: {course.id})")
        
        # Store course info for response
        course_title = course.title
        
        # Delete the course
        course.delete()
        
        logger.info(f"✅ Practice course deleted successfully: {course_title}")
        
        return Response({
            'message': f'Curso "{course_title}" excluído com sucesso',
            'success': True
        }, status=status.HTTP_200_OK)
    
    def put(self, request, course_id):
        """Publish/Unpublish practice course"""
        course = self.get_object(course_id)
        
        # Get action from request data
        action = request.data.get('action')  # 'publish' or 'unpublish'
        
        if action == 'publish':
            if course.status == 'Published':
                return Response({
                    'message': 'Curso já está publicado',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            
            course.status = 'Published'
            course.save()
            
            logger.info(f"📢 Practice course published: {course.title} (ID: {course.id})")
            
            return Response({
                'message': f'Curso "{course.title}" publicado com sucesso',
                'success': True,
                'status': 'Published'
            }, status=status.HTTP_200_OK)
            
        elif action == 'unpublish':
            if course.status == 'Draft':
                return Response({
                    'message': 'Curso já está em rascunho',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            
            course.status = 'Draft'
            course.save()
            
            logger.info(f"📝 Practice course unpublished: {course.title} (ID: {course.id})")
            
            return Response({
                'message': f'Curso "{course.title}" despublicado com sucesso',
                'success': True,
                'status': 'Draft'
            }, status=status.HTTP_200_OK)
            
        else:
            return Response({
                'message': 'Ação inválida. Use "publish" ou "unpublish"',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)