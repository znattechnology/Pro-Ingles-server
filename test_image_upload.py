#!/usr/bin/env python
"""
Test script for image upload endpoint
"""

import os
import django
import requests
import tempfile
from PIL import Image
import io

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.courses.models import Course

def create_test_image():
    """Create a simple test image in memory"""
    # Create a small test image
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return img_io

def test_image_upload():
    """Test the image upload endpoint"""
    print("🧪 Testing image upload endpoint...")
    
    # Get a teacher and course for testing
    teacher = User.objects.filter(role='teacher').first()
    if not teacher:
        print("❌ No teacher found")
        return
    
    course = Course.objects.filter(teacher=teacher).first()
    if not course:
        print("❌ No course found for teacher")
        return
    
    print(f"👨‍🏫 Using teacher: {teacher.name}")
    print(f"📚 Using course: {course.title} (ID: {course.id})")
    
    # Create test image
    test_image = create_test_image()
    
    # Simulate login to get token (this is simplified)
    login_data = {
        'email': teacher.email,
        'password': 'testpassword'  # This won't work in real scenario
    }
    
    print("\n🌐 Testing upload endpoint directly...")
    
    # Test the endpoint
    url = f"http://localhost:8000/api/v1/courses/{course.id}/upload-image/"
    
    # We'll skip the actual HTTP request since we don't have real authentication
    # Instead, let's test the Django view directly
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from apps.courses.views import upload_course_image
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create a request factory
    factory = RequestFactory()
    
    # Create a test image file
    test_file = SimpleUploadedFile(
        name='test_image.jpg',
        content=test_image.read(),
        content_type='image/jpeg'
    )
    
    # Create the request
    request = factory.post(f'/api/v1/courses/{course.id}/upload-image/', {
        'image': test_file
    })
    request.user = teacher
    
    # Mock authentication
    from unittest.mock import Mock
    request.auth = Mock()
    request.META = {'HTTP_AUTHORIZATION': 'Bearer test-token'}
    
    print("📤 Calling upload_course_image view directly...")
    
    try:
        response = upload_course_image(request, str(course.id))
        print(f"✅ Response status: {response.status_code}")
        print(f"   Response data: {response.data}")
    except Exception as e:
        print(f"❌ Error calling view: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_image_upload()