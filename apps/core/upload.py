"""
Centralized file upload handling system.
Supports single and multiple file uploads with validation and processing.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class FileUploadHandler:
    """
    Centralized file upload handler with validation, processing and optimization.
    """
    
    # Supported file types
    SUPPORTED_IMAGE_TYPES = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg', 
        'image/png': '.png',
        'image/webp': '.webp',
        'image/gif': '.gif',
    }
    
    SUPPORTED_DOCUMENT_TYPES = {
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
    }
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 25 * 1024 * 1024  # 25MB
    
    # Image optimization settings
    IMAGE_QUALITY = 85
    MAX_IMAGE_DIMENSION = 2048
    THUMBNAIL_SIZE = (300, 300)
    
    def __init__(self, upload_type: str = 'general', user=None):
        """
        Initialize upload handler.
        
        Args:
            upload_type: Type of upload (portfolio, service, profile, document)
            user: User performing the upload
        """
        self.upload_type = upload_type
        self.user = user
        self.allowed_types = {**self.SUPPORTED_IMAGE_TYPES, **self.SUPPORTED_DOCUMENT_TYPES}
        
        # Set specific restrictions based on upload type
        if upload_type in ['portfolio', 'service', 'profile']:
            self.allowed_types = self.SUPPORTED_IMAGE_TYPES
            self.max_file_size = self.MAX_IMAGE_SIZE
        elif upload_type == 'document':
            self.allowed_types = self.SUPPORTED_DOCUMENT_TYPES
            self.max_file_size = self.MAX_DOCUMENT_SIZE
        else:
            self.max_file_size = self.MAX_IMAGE_SIZE
    
    def validate_file(self, file) -> Dict[str, Any]:
        """
        Validate uploaded file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dict with validation results
        """
        errors = []
        
        # Check file size
        if file.size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            errors.append(f'File size ({file.size / (1024 * 1024):.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)')
        
        # Check file type
        content_type = getattr(file, 'content_type', None)
        if content_type not in self.allowed_types:
            allowed_types = ', '.join(self.allowed_types.keys())
            errors.append(f'File type "{content_type}" not allowed. Allowed types: {allowed_types}')
        
        # Check file name
        if not file.name:
            errors.append('File name is required')
        elif len(file.name) > 255:
            errors.append('File name too long (max 255 characters)')
        
        # Additional validation for images
        if content_type in self.SUPPORTED_IMAGE_TYPES:
            try:
                image = Image.open(file)
                # Check image dimensions
                width, height = image.size
                if width > 4000 or height > 4000:
                    errors.append(f'Image dimensions ({width}x{height}) too large. Maximum: 4000x4000')
                
                # Verify image integrity
                image.verify()
            except Exception as e:
                errors.append(f'Invalid image file: {str(e)}')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'content_type': content_type,
            'size': file.size,
            'name': file.name
        }
    
    def generate_file_path(self, original_filename: str, content_type: str) -> str:
        """
        Generate unique file path for upload.
        
        Args:
            original_filename: Original file name
            content_type: MIME type of file
            
        Returns:
            Generated file path
        """
        # Extract file extension
        file_extension = self.allowed_types.get(content_type, '')
        if not file_extension and '.' in original_filename:
            file_extension = '.' + original_filename.split('.')[-1].lower()
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        safe_filename = slugify(os.path.splitext(original_filename)[0])[:50]
        filename = f"{safe_filename}_{unique_id}{file_extension}"
        
        # Generate path based on upload type and user
        if self.user:
            user_folder = f"user_{self.user.id}"
        else:
            user_folder = "anonymous"
        
        file_path = os.path.join(
            'uploads',
            self.upload_type,
            user_folder,
            filename
        )
        
        return file_path
    
    def optimize_image(self, image_file, output_path: str) -> Dict[str, Any]:
        """
        Optimize image file (resize, compress, create thumbnail).
        
        Args:
            image_file: PIL Image object or file path
            output_path: Output file path
            
        Returns:
            Dict with optimization results
        """
        try:
            if isinstance(image_file, str):
                image = Image.open(image_file)
            else:
                image = Image.open(image_file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            original_size = image.size
            
            # Resize if too large
            if image.width > self.MAX_IMAGE_DIMENSION or image.height > self.MAX_IMAGE_DIMENSION:
                image.thumbnail((self.MAX_IMAGE_DIMENSION, self.MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            
            # Save optimized image
            image.save(output_path, 'JPEG', quality=self.IMAGE_QUALITY, optimize=True)
            
            # Create thumbnail
            thumbnail_path = output_path.replace('.jpg', '_thumb.jpg')
            thumb_image = image.copy()
            thumb_image.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            thumb_image.save(thumbnail_path, 'JPEG', quality=80, optimize=True)
            
            return {
                'success': True,
                'original_size': original_size,
                'optimized_size': image.size,
                'main_path': output_path,
                'thumbnail_path': thumbnail_path,
                'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
            }
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_single_file(self, file) -> Dict[str, Any]:
        """
        Upload and process a single file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dict with upload results
        """
        # Validate file
        validation = self.validate_file(file)
        if not validation['is_valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        try:
            # Generate file path
            file_path = self.generate_file_path(file.name, validation['content_type'])
            
            # Save file
            saved_path = default_storage.save(file_path, file)
            full_path = default_storage.path(saved_path)
            
            result = {
                'success': True,
                'file_path': saved_path,
                'file_url': default_storage.url(saved_path),
                'original_name': file.name,
                'content_type': validation['content_type'],
                'size': validation['size'],
                'is_image': validation['content_type'] in self.SUPPORTED_IMAGE_TYPES
            }
            
            # Optimize if image
            if validation['content_type'] in self.SUPPORTED_IMAGE_TYPES:
                optimization = self.optimize_image(full_path, full_path)
                if optimization['success']:
                    result.update({
                        'thumbnail_url': default_storage.url(optimization['thumbnail_path']),
                        'original_dimensions': optimization['original_size'],
                        'optimized_dimensions': optimization['optimized_size'],
                        'optimized_size': optimization['file_size']
                    })
                else:
                    logger.warning(f"Image optimization failed for {saved_path}: {optimization.get('error')}")
            
            logger.info(f"File uploaded successfully: {saved_path}")
            return result
            
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            return {
                'success': False,
                'errors': [f'Upload failed: {str(e)}']
            }
    
    def upload_multiple_files(self, files: List) -> Dict[str, Any]:
        """
        Upload and process multiple files.
        
        Args:
            files: List of uploaded file objects
            
        Returns:
            Dict with upload results for all files
        """
        if not files:
            return {
                'success': False,
                'errors': ['No files provided']
            }
        
        # Validate file count
        max_files = 20 if self.upload_type == 'portfolio' else 10
        if len(files) > max_files:
            return {
                'success': False,
                'errors': [f'Too many files. Maximum allowed: {max_files}']
            }
        
        results = {
            'success': True,
            'uploaded_files': [],
            'failed_files': [],
            'total_files': len(files),
            'successful_uploads': 0,
            'failed_uploads': 0
        }
        
        for i, file in enumerate(files):
            upload_result = self.upload_single_file(file)
            
            if upload_result['success']:
                upload_result['upload_index'] = i
                results['uploaded_files'].append(upload_result)
                results['successful_uploads'] += 1
            else:
                results['failed_files'].append({
                    'file_name': getattr(file, 'name', f'file_{i}'),
                    'upload_index': i,
                    'errors': upload_result['errors']
                })
                results['failed_uploads'] += 1
        
        # Overall success if at least one file uploaded
        results['success'] = results['successful_uploads'] > 0
        
        if results['failed_uploads'] > 0:
            results['partial_success'] = True
        
        logger.info(f"Multiple file upload completed: {results['successful_uploads']}/{results['total_files']} successful")
        return results


class PortfolioUploadHandler(FileUploadHandler):
    """Specialized handler for portfolio image uploads."""
    
    def __init__(self, braider, **kwargs):
        super().__init__(upload_type='portfolio', user=braider.user, **kwargs)
        self.braider = braider
    
    def process_portfolio_upload(self, files: List, titles: Optional[List[str]] = None, 
                               descriptions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process portfolio images with metadata.
        
        Args:
            files: List of image files
            titles: Optional list of titles for each image
            descriptions: Optional list of descriptions for each image
            
        Returns:
            Processing results with created portfolio items
        """
        upload_result = self.upload_multiple_files(files)
        
        if not upload_result['success']:
            return upload_result
        
        from apps.braiders.models import BraiderPortfolioImage
        
        created_items = []
        
        for i, file_data in enumerate(upload_result['uploaded_files']):
            try:
                # Get metadata for this image
                title = titles[i] if titles and i < len(titles) else ''
                description = descriptions[i] if descriptions and i < len(descriptions) else ''
                upload_index = file_data['upload_index']
                
                # Create portfolio item
                portfolio_item = BraiderPortfolioImage.objects.create(
                    braider=self.braider,
                    image=file_data['file_path'],
                    title=title or f"Portfolio Image {upload_index + 1}",
                    description=description,
                    order=upload_index
                )
                
                created_items.append({
                    'id': str(portfolio_item.id),
                    'title': portfolio_item.title,
                    'description': portfolio_item.description,
                    'image_url': file_data['file_url'],
                    'thumbnail_url': file_data.get('thumbnail_url'),
                    'order': portfolio_item.order,
                    'upload_index': upload_index
                })
                
            except Exception as e:
                logger.error(f"Failed to create portfolio item for file {i}: {str(e)}")
                upload_result['failed_files'].append({
                    'file_name': file_data['original_name'],
                    'upload_index': file_data['upload_index'],
                    'errors': [f'Database error: {str(e)}']
                })
                upload_result['failed_uploads'] += 1
                upload_result['successful_uploads'] -= 1
        
        upload_result['portfolio_items'] = created_items
        upload_result['success'] = len(created_items) > 0
        
        return upload_result


class ServiceImageUploadHandler(FileUploadHandler):
    """Specialized handler for service image uploads."""
    
    def __init__(self, service, **kwargs):
        super().__init__(upload_type='service', user=service.braider.user, **kwargs)
        self.service = service
    
    def process_service_images(self, files: List, set_as_main: bool = False) -> Dict[str, Any]:
        """
        Process service images.
        
        Args:
            files: List of image files
            set_as_main: Whether to set first image as main service image
            
        Returns:
            Processing results
        """
        upload_result = self.upload_multiple_files(files)
        
        if not upload_result['success']:
            return upload_result
        
        from apps.braiders.models import ServiceImage
        
        created_items = []
        
        for i, file_data in enumerate(upload_result['uploaded_files']):
            try:
                upload_index = file_data['upload_index']
                
                # Create service image
                service_image = ServiceImage.objects.create(
                    service=self.service,
                    image=file_data['file_path'],
                    alt_text=f"{self.service.name} - Image {upload_index + 1}",
                    order=upload_index
                )
                
                created_items.append({
                    'id': str(service_image.id),
                    'image_url': file_data['file_url'],
                    'thumbnail_url': file_data.get('thumbnail_url'),
                    'alt_text': service_image.alt_text,
                    'order': service_image.order,
                    'upload_index': upload_index
                })
                
                # Set as main service image if requested and first image
                if set_as_main and i == 0:
                    self.service.main_image = file_data['file_path']
                    self.service.save(update_fields=['main_image'])
                    created_items[-1]['is_main'] = True
                
            except Exception as e:
                logger.error(f"Failed to create service image for file {i}: {str(e)}")
                upload_result['failed_files'].append({
                    'file_name': file_data['original_name'],
                    'upload_index': file_data['upload_index'],
                    'errors': [f'Database error: {str(e)}']
                })
        
        upload_result['service_images'] = created_items
        return upload_result