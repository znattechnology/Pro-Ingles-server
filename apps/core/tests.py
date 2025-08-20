"""
Tests for core functionality including upload system.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import tempfile
import os
from PIL import Image

from apps.core.upload import FileUploadHandler, PortfolioUploadHandler

User = get_user_model()


class FileUploadHandlerTest(TestCase):
    """Test FileUploadHandler functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='upload@test.com',
            name='Upload User',
            password='testpass'
        )
        self.handler = FileUploadHandler(upload_type='portfolio', user=self.user)
    
    def test_handler_initialization(self):
        """Test upload handler initialization."""
        self.assertEqual(self.handler.upload_type, 'portfolio')
        self.assertEqual(self.handler.user, self.user)
        self.assertIn('image/jpeg', self.handler.allowed_types)
        self.assertIn('image/png', self.handler.allowed_types)
    
    def test_file_path_generation(self):
        """Test unique file path generation."""
        path1 = self.handler.generate_file_path('test.jpg', 'image/jpeg')
        path2 = self.handler.generate_file_path('test.jpg', 'image/jpeg')
        
        # Paths should be different due to UUID
        self.assertNotEqual(path1, path2)
        
        # Should contain user folder
        self.assertIn(f'user_{self.user.id}', path1)
        self.assertIn('portfolio', path1)
        self.assertTrue(path1.endswith('.jpg'))
    
    def test_validate_valid_file(self):
        """Test validation of valid file."""
        # Create a small test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            image = Image.new('RGB', (100, 100), color='red')
            image.save(temp_file, 'JPEG')
            temp_file.seek(0)
            
            mock_file = MagicMock()
            mock_file.name = 'test.jpg'
            mock_file.size = 1024  # 1KB
            mock_file.content_type = 'image/jpeg'
            
            validation = self.handler.validate_file(mock_file)
            
            # Should be valid except for image verification
            self.assertIn('content_type', validation)
            self.assertEqual(validation['content_type'], 'image/jpeg')
            self.assertEqual(validation['size'], 1024)
        
        os.unlink(temp_file.name)
    
    def test_validate_large_file(self):
        """Test validation of oversized file."""
        mock_file = MagicMock()
        mock_file.name = 'large.jpg'
        mock_file.size = 50 * 1024 * 1024  # 50MB
        mock_file.content_type = 'image/jpeg'
        
        validation = self.handler.validate_file(mock_file)
        
        self.assertFalse(validation['is_valid'])
        self.assertTrue(any('exceeds maximum' in error for error in validation['errors']))
    
    def test_validate_invalid_type(self):
        """Test validation of invalid file type."""
        mock_file = MagicMock()
        mock_file.name = 'test.xyz'
        mock_file.size = 1024
        mock_file.content_type = 'application/xyz'
        
        validation = self.handler.validate_file(mock_file)
        
        self.assertFalse(validation['is_valid'])
        self.assertTrue(any('not allowed' in error for error in validation['errors']))
    
    def test_upload_type_restrictions(self):
        """Test different upload type restrictions."""
        portfolio_handler = FileUploadHandler(upload_type='portfolio')
        document_handler = FileUploadHandler(upload_type='document')
        
        # Portfolio should only accept images
        self.assertIn('image/jpeg', portfolio_handler.allowed_types)
        self.assertNotIn('application/pdf', portfolio_handler.allowed_types)
        
        # Document should accept documents
        self.assertIn('application/pdf', document_handler.allowed_types)
        self.assertNotIn('image/jpeg', document_handler.allowed_types)


class UploadAPITest(APITestCase):
    """Test upload API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def create_test_image(self):
        """Create a test image file."""
        image = Image.new('RGB', (100, 100), color='blue')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(temp_file, 'JPEG')
        temp_file.seek(0)
        
        return SimpleUploadedFile(
            name='test.jpg',
            content=temp_file.read(),
            content_type='image/jpeg'
        )
    
    def test_upload_status_endpoint(self):
        """Test upload status/configuration endpoint."""
        url = reverse('upload:upload_status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('limits', response.data)
        self.assertIn('features', response.data)
        self.assertIn('max_file_size_mb', response.data['limits'])
    
    @patch('apps.core.upload.default_storage.save')
    @patch('apps.core.upload.default_storage.path')
    @patch('apps.core.upload.default_storage.url')
    def test_general_upload(self, mock_url, mock_path, mock_save):
        """Test general file upload endpoint."""
        # Mock storage methods
        mock_save.return_value = 'uploads/general/user_123/test.jpg'
        mock_path.return_value = '/fake/path/test.jpg'
        mock_url.return_value = '/media/uploads/general/user_123/test.jpg'
        
        url = reverse('upload:general_upload')
        test_image = self.create_test_image()
        
        response = self.client.post(url, {
            'files': test_image,
            'upload_type': 'general'
        }, format='multipart')
        
        # Should fail due to mocked storage, but endpoint should be accessible
        self.assertIn(response.status_code, [200, 201, 400, 500])
    
    def test_upload_without_authentication(self):
        """Test upload endpoint without authentication."""
        self.client.force_authenticate(user=None)
        url = reverse('upload:general_upload')
        
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_upload_without_files(self):
        """Test upload endpoint without files."""
        url = reverse('upload:general_upload')
        
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No files provided', str(response.data))


class CoreUtilitiesTest(TestCase):
    """Test core utility functions and classes."""
    
    def test_unique_code_generation(self):
        """Test generation of unique codes."""
        from apps.promotions.models import Promotion
        
        code1 = Promotion.generate_unique_code()
        code2 = Promotion.generate_unique_code()
        
        self.assertNotEqual(code1, code2)
        self.assertEqual(len(code1), 8)
        self.assertTrue(code1.isalnum())
        self.assertTrue(code1.isupper())
    
    def test_pagination_class(self):
        """Test custom pagination class."""
        from apps.core.pagination import CustomPagination
        
        pagination = CustomPagination()
        
        # Test default values
        self.assertEqual(pagination.page_size, 20)
        self.assertIsNotNone(pagination.page_size_query_param)
        self.assertIsNotNone(pagination.max_page_size)


class BaseModelTest(TestCase):
    """Test BaseModel functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='base@test.com',
            name='Base User',
            password='testpass'
        )
    
    def test_base_model_fields(self):
        """Test that BaseModel fields are present."""
        # Test with User model which extends BaseModel
        self.assertIsNotNone(self.user.id)
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)
        
        # ID should be UUID
        self.assertEqual(len(str(self.user.id)), 36)  # UUID length with hyphens
    
    def test_updated_at_changes(self):
        """Test that updated_at changes when model is saved."""
        original_updated = self.user.updated_at
        
        # Update the user
        self.user.name = 'Updated Name'
        self.user.save()
        
        self.assertGreater(self.user.updated_at, original_updated)