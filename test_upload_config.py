#!/usr/bin/env python3
"""
Test script to verify S3 upload configuration
"""

import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_s3_configuration():
    print("🔍 Testing S3 Configuration...")
    print("=" * 50)
    
    # Check environment variables
    print(f"USE_S3: {settings.USE_S3}")
    print(f"AWS_ACCESS_KEY_ID: {'✅ Set' if settings.AWS_ACCESS_KEY_ID else '❌ Missing'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'✅ Set' if settings.AWS_SECRET_ACCESS_KEY else '❌ Missing'}")
    print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME or '❌ Missing'}")
    print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME or '❌ Missing'}")
    
    if hasattr(settings, 'CLOUDFRONT_DOMAIN'):
        print(f"CLOUDFRONT_DOMAIN: {getattr(settings, 'CLOUDFRONT_DOMAIN', '❌ Missing')}")
    
    print("\n" + "=" * 50)
    
    # Test S3 connection if configured
    if settings.USE_S3 and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            print("🧪 Testing S3 Connection...")
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            # Test bucket access
            try:
                s3_client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                print("✅ S3 bucket access: SUCCESS")
                
                # Try to generate a presigned URL
                try:
                    test_key = "test-videos/test-upload.mp4"
                    presigned_url = s3_client.generate_presigned_url(
                        'put_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': test_key,
                            'ContentType': 'video/mp4'
                        },
                        ExpiresIn=3600
                    )
                    print("✅ Presigned URL generation: SUCCESS")
                    print(f"📝 Sample URL: {presigned_url[:80]}...")
                    
                except ClientError as e:
                    print(f"❌ Presigned URL generation failed: {e}")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '403':
                    print("❌ S3 bucket access: FORBIDDEN (Check permissions)")
                elif error_code == '404':
                    print("❌ S3 bucket access: NOT FOUND (Check bucket name)")
                else:
                    print(f"❌ S3 bucket access failed: {e}")
                    
        except ImportError:
            print("❌ boto3 not installed")
        except Exception as e:
            print(f"❌ S3 connection test failed: {e}")
    else:
        print("⚠️  S3 not fully configured - skipping connection test")
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    
    # Configuration checklist
    config_complete = True
    checklist = []
    
    if not settings.USE_S3:
        checklist.append("❌ USE_S3 is False")
        config_complete = False
    else:
        checklist.append("✅ USE_S3 is True")
    
    if not settings.AWS_ACCESS_KEY_ID or settings.AWS_ACCESS_KEY_ID == 'your-aws-access-key-here':
        checklist.append("❌ AWS_ACCESS_KEY_ID not configured")
        config_complete = False
    else:
        checklist.append("✅ AWS_ACCESS_KEY_ID configured")
    
    if not settings.AWS_SECRET_ACCESS_KEY or settings.AWS_SECRET_ACCESS_KEY == 'your-aws-secret-key-here':
        checklist.append("❌ AWS_SECRET_ACCESS_KEY not configured")
        config_complete = False
    else:
        checklist.append("✅ AWS_SECRET_ACCESS_KEY configured")
    
    if not settings.AWS_STORAGE_BUCKET_NAME:
        checklist.append("❌ AWS_STORAGE_BUCKET_NAME not configured")
        config_complete = False
    else:
        checklist.append("✅ AWS_STORAGE_BUCKET_NAME configured")
    
    for item in checklist:
        print(item)
    
    print(f"\n🎯 VIDEO UPLOAD STATUS: {'✅ READY' if config_complete else '❌ NOT READY'}")
    
    if not config_complete:
        print("\n🛠️  TO FIX:")
        print("1. Add your real AWS credentials to .env file")
        print("2. Restart Django server")
        print("3. Run this test again")

if __name__ == "__main__":
    test_s3_configuration()