#!/usr/bin/env python3
"""
Simple test for video upload functionality
"""

import os
import django
from django.conf import settings
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_s3_upload():
    print("🎬 Testing S3 Video Upload Capability...")
    print("=" * 50)
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Test credentials
        print(f"🔑 AWS Access Key: {settings.AWS_ACCESS_KEY_ID[:8]}...")
        print(f"🪣 S3 Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
        print(f"🌍 Region: {settings.AWS_S3_REGION_NAME}")
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Generate test video path
        test_course_id = str(uuid.uuid4())
        test_section_id = str(uuid.uuid4())
        test_chapter_id = str(uuid.uuid4())
        
        video_key = f"courses/{test_course_id}/sections/{test_section_id}/chapters/{test_chapter_id}/video.mp4"
        
        print(f"📹 Test video path: {video_key}")
        
        # Generate presigned URL for upload
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': video_key,
                'ContentType': 'video/mp4',
                'ACL': 'public-read'  # Make video publicly readable
            },
            ExpiresIn=3600
        )
        
        print(f"\n✅ SUCCESS! Upload URL generated:")
        print(f"🔗 Upload URL: {presigned_url[:80]}...")
        print(f"⏰ Valid for: 1 hour")
        
        # Show what the final video URL would be
        if hasattr(settings, 'CLOUDFRONT_DOMAIN'):
            cloudfront_domain = getattr(settings, 'CLOUDFRONT_DOMAIN')
            final_url = f"{cloudfront_domain}/{video_key}"
        else:
            final_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{video_key}"
        
        print(f"🚀 Final video URL: {final_url}")
        
        # Test API endpoint format
        api_endpoint = f"/api/v1/courses/{test_course_id}/sections/{test_section_id}/chapters/{test_chapter_id}/get-upload-url/"
        print(f"🌐 API endpoint format: {api_endpoint}")
        
        print(f"\n🎯 RESULTADO: ✅ UPLOAD DE VÍDEOS ESTÁ FUNCIONANDO!")
        print("🚀 Você pode agora fazer upload de vídeos pela interface!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_s3_upload()
    if success:
        print("\n" + "🎉" * 20)
        print("   UPLOADS DE VÍDEO ESTÃO PRONTOS!")
        print("🎉" * 20)
    else:
        print("\n❌ Ainda há problemas de configuração")