"""
Upload API views for handling file uploads across the platform.
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
import logging

from .upload import FileUploadHandler, PortfolioUploadHandler, ServiceImageUploadHandler
from apps.braiders.models import Braider, Service
from apps.core.permissions import IsBraider

logger = logging.getLogger(__name__)


class GeneralFileUploadView(APIView):
    """
    General file upload endpoint for single or multiple files.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Upload one or more files.
        
        Expected form data:
        - files: Single file or multiple files
        - upload_type: Type of upload (general, document, etc.)
        """
        upload_type = request.data.get('upload_type', 'general')
        files = request.FILES.getlist('files')
        
        if not files:
            return Response({
                'success': False,
                'errors': ['No files provided']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        handler = FileUploadHandler(upload_type=upload_type, user=request.user)
        
        if len(files) == 1:
            result = handler.upload_single_file(files[0])
        else:
            result = handler.upload_multiple_files(files)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class PortfolioUploadView(APIView):
    """
    Portfolio image upload endpoint for braiders.
    """
    permission_classes = [IsBraider]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Upload portfolio images with metadata.
        
        Expected form data:
        - images: Multiple image files
        - titles[]: Array of titles (optional)
        - descriptions[]: Array of descriptions (optional)
        """
        try:
            braider = get_object_or_404(Braider, user=request.user)
        except Braider.DoesNotExist:
            return Response({
                'success': False,
                'errors': ['Braider profile not found']
            }, status=status.HTTP_404_NOT_FOUND)
        
        images = request.FILES.getlist('images')
        if not images:
            return Response({
                'success': False,
                'errors': ['No images provided']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get metadata arrays
        titles = request.data.getlist('titles[]') or []
        descriptions = request.data.getlist('descriptions[]') or []
        
        # Validate image count
        if len(images) > 20:
            return Response({
                'success': False,
                'errors': ['Maximum 20 images allowed per upload']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        handler = PortfolioUploadHandler(braider=braider)
        result = handler.process_portfolio_upload(
            files=images,
            titles=titles,
            descriptions=descriptions
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class ServiceImageUploadView(APIView):
    """
    Service image upload endpoint for braiders.
    """
    permission_classes = [IsBraider]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, service_id):
        """
        Upload service images.
        
        Expected form data:
        - images: Multiple image files
        - set_as_main: Boolean to set first image as main (optional)
        """
        try:
            braider = get_object_or_404(Braider, user=request.user)
            service = get_object_or_404(Service, id=service_id, braider=braider)
        except (Braider.DoesNotExist, Service.DoesNotExist):
            return Response({
                'success': False,
                'errors': ['Service not found or access denied']
            }, status=status.HTTP_404_NOT_FOUND)
        
        images = request.FILES.getlist('images')
        if not images:
            return Response({
                'success': False,
                'errors': ['No images provided']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate image count
        if len(images) > 10:
            return Response({
                'success': False,
                'errors': ['Maximum 10 images allowed per service']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        set_as_main = request.data.get('set_as_main', '').lower() in ['true', '1', 'yes']
        
        handler = ServiceImageUploadHandler(service=service)
        result = handler.process_service_images(
            files=images,
            set_as_main=set_as_main
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageUploadView(APIView):
    """
    Profile image upload endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Upload profile image.
        
        Expected form data:
        - image: Single image file
        - profile_type: 'user' or 'braider'
        """
        image = request.FILES.get('image')
        if not image:
            return Response({
                'success': False,
                'errors': ['No image provided']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_type = request.data.get('profile_type', 'user')
        
        handler = FileUploadHandler(upload_type='profile', user=request.user)
        result = handler.upload_single_file(image)
        
        if result['success']:
            # Update profile based on type
            try:
                if profile_type == 'braider':
                    braider = get_object_or_404(Braider, user=request.user)
                    braider.profile_image = result['file_path']
                    braider.save(update_fields=['profile_image'])
                    result['profile_updated'] = True
                    result['profile_type'] = 'braider'
                else:
                    # Update user avatar
                    request.user.avatar = result['file_path']
                    request.user.save(update_fields=['avatar'])
                    result['profile_updated'] = True
                    result['profile_type'] = 'user'
                
            except Exception as e:
                logger.warning(f"Profile update failed after upload: {str(e)}")
                result['profile_updated'] = False
                result['profile_update_error'] = str(e)
            
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def upload_status_view(request):
    """
    Get upload limits and configuration for the current user.
    """
    is_braider = hasattr(request.user, 'braider_profile')
    
    return Response({
        'user_type': 'braider' if is_braider else 'customer',
        'limits': {
            'max_file_size_mb': 10,
            'max_image_dimension': 2048,
            'max_portfolio_images': 20,
            'max_service_images': 10,
            'supported_image_types': ['image/jpeg', 'image/png', 'image/webp'],
            'supported_document_types': ['application/pdf', 'application/msword', 'text/plain']
        },
        'features': {
            'can_upload_portfolio': is_braider,
            'can_upload_service_images': is_braider,
            'image_optimization': True,
            'thumbnail_generation': True,
            'batch_upload': True
        }
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_uploaded_file_view(request, file_path):
    """
    Delete an uploaded file (with proper authorization).
    
    Args:
        file_path: Encoded file path to delete
    """
    import base64
    from django.core.files.storage import default_storage
    
    try:
        # Decode file path
        decoded_path = base64.urlsafe_b64decode(file_path.encode()).decode()
        
        # Verify user owns this file (basic security check)
        if f"user_{request.user.id}" not in decoded_path:
            return Response({
                'success': False,
                'errors': ['Access denied']
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete file
        if default_storage.exists(decoded_path):
            default_storage.delete(decoded_path)
            
            # Try to delete thumbnail too
            if decoded_path.endswith('.jpg'):
                thumb_path = decoded_path.replace('.jpg', '_thumb.jpg')
                if default_storage.exists(thumb_path):
                    default_storage.delete(thumb_path)
            
            return Response({
                'success': True,
                'message': 'File deleted successfully'
            })
        else:
            return Response({
                'success': False,
                'errors': ['File not found']
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
        return Response({
            'success': False,
            'errors': ['File deletion failed']
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatchUploadView(APIView):
    """
    Batch upload endpoint for multiple files of different types.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Handle batch upload with different file types and destinations.
        
        Expected form data:
        - files: Multiple files
        - file_types[]: Array indicating type for each file
        - destinations[]: Array indicating destination for each file
        """
        files = request.FILES.getlist('files')
        file_types = request.data.getlist('file_types[]') or []
        destinations = request.data.getlist('destinations[]') or []
        
        if not files:
            return Response({
                'success': False,
                'errors': ['No files provided']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {
            'success': True,
            'total_files': len(files),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'upload_results': []
        }
        
        for i, file in enumerate(files):
            file_type = file_types[i] if i < len(file_types) else 'general'
            destination = destinations[i] if i < len(destinations) else 'general'
            
            try:
                handler = FileUploadHandler(upload_type=file_type, user=request.user)
                result = handler.upload_single_file(file)
                
                result['file_index'] = i
                result['destination'] = destination
                results['upload_results'].append(result)
                
                if result['success']:
                    results['successful_uploads'] += 1
                else:
                    results['failed_uploads'] += 1
                    
            except Exception as e:
                logger.error(f"Batch upload failed for file {i}: {str(e)}")
                results['upload_results'].append({
                    'success': False,
                    'file_index': i,
                    'errors': [f'Upload failed: {str(e)}'],
                    'original_name': getattr(file, 'name', f'file_{i}')
                })
                results['failed_uploads'] += 1
        
        results['success'] = results['successful_uploads'] > 0
        
        if results['success']:
            return Response(results, status=status.HTTP_201_CREATED)
        else:
            return Response(results, status=status.HTTP_400_BAD_REQUEST)