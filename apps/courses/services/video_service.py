"""
Video URL Security Service

This service handles the generation of signed URLs for video content.
It supports both CloudFront signed URLs and S3 presigned URLs.

SECURITY: Videos should not be accessible via permanent public URLs.
This service generates temporary URLs that expire after a configured time.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)

# Default URL expiration time in seconds (4 hours)
DEFAULT_URL_EXPIRATION = 4 * 60 * 60


class VideoURLService:
    """
    Service for generating secure, expiring URLs for video content.

    Supports:
    - CloudFront signed URLs (preferred, requires key pair configuration)
    - S3 presigned URLs (fallback, works with standard AWS credentials)
    """

    def __init__(self):
        self.use_cloudfront = self._check_cloudfront_config()
        self.s3_client = None

    def _check_cloudfront_config(self) -> bool:
        """Check if CloudFront signing is properly configured."""
        required_settings = [
            'AWS_CLOUDFRONT_KEY_ID',
            'AWS_CLOUDFRONT_PRIVATE_KEY_PATH',
            'AWS_CLOUDFRONT_DOMAIN',
        ]
        return all(hasattr(settings, s) and getattr(settings, s) for s in required_settings)

    def _get_s3_client(self):
        """Lazy initialization of S3 client."""
        if self.s3_client is None:
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
            )
        return self.s3_client

    def generate_signed_url(
        self,
        video_url: str,
        expiration_seconds: int = DEFAULT_URL_EXPIRATION
    ) -> str:
        """
        Generate a signed URL for video content.

        Args:
            video_url: The original video URL (CloudFront or S3)
            expiration_seconds: How long the URL should be valid

        Returns:
            A signed URL that expires after the specified time
        """
        if not video_url:
            return video_url

        # If CloudFront is configured and URL is a CloudFront URL, use CloudFront signing
        if self.use_cloudfront and self._is_cloudfront_url(video_url):
            return self._generate_cloudfront_signed_url(video_url, expiration_seconds)

        # Otherwise, try S3 presigned URL
        if self._is_s3_url(video_url):
            return self._generate_s3_presigned_url(video_url, expiration_seconds)

        # If neither, return original URL (might be external)
        logger.warning(f"Could not sign URL (not CloudFront or S3): {video_url[:50]}...")
        return video_url

    def _is_cloudfront_url(self, url: str) -> bool:
        """Check if URL is a CloudFront URL."""
        if not url:
            return False
        cloudfront_domain = getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', '')
        return cloudfront_domain and cloudfront_domain in url

    def _is_s3_url(self, url: str) -> bool:
        """Check if URL is an S3 URL."""
        if not url:
            return False
        s3_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '')
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        return (
            (s3_domain and s3_domain in url) or
            (bucket_name and f"{bucket_name}.s3" in url) or
            's3.amazonaws.com' in url
        )

    def _generate_cloudfront_signed_url(
        self,
        url: str,
        expiration_seconds: int
    ) -> str:
        """
        Generate a CloudFront signed URL.

        Requires:
        - AWS_CLOUDFRONT_KEY_ID: The CloudFront key pair ID
        - AWS_CLOUDFRONT_PRIVATE_KEY_PATH: Path to the private key file
        """
        try:
            from botocore.signers import CloudFrontSigner
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend

            key_id = settings.AWS_CLOUDFRONT_KEY_ID
            private_key_path = settings.AWS_CLOUDFRONT_PRIVATE_KEY_PATH

            # Load the private key
            with open(private_key_path, 'rb') as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=default_backend()
                )

            # Create RSA signer
            def rsa_signer(message):
                return private_key.sign(
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA1()
                )

            # Create CloudFront signer
            cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)

            # Calculate expiration time
            expire_date = datetime.utcnow() + timedelta(seconds=expiration_seconds)

            # Generate signed URL
            signed_url = cloudfront_signer.generate_presigned_url(
                url,
                date_less_than=expire_date
            )

            return signed_url

        except ImportError as e:
            logger.warning(f"CloudFront signing not available (missing dependency): {e}")
            return url
        except FileNotFoundError:
            logger.error(f"CloudFront private key not found at: {private_key_path}")
            return url
        except Exception as e:
            logger.error(f"Error generating CloudFront signed URL: {e}")
            return url

    def _generate_s3_presigned_url(
        self,
        url: str,
        expiration_seconds: int
    ) -> str:
        """
        Generate an S3 presigned URL.

        This is a fallback when CloudFront signing is not available.
        """
        try:
            # Extract bucket and key from URL
            bucket, key = self._parse_s3_url(url)

            if not bucket or not key:
                logger.warning(f"Could not parse S3 URL: {url[:50]}...")
                return url

            s3_client = self._get_s3_client()

            # Generate presigned URL for GET operation
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': key
                },
                ExpiresIn=expiration_seconds
            )

            return presigned_url

        except Exception as e:
            logger.error(f"Error generating S3 presigned URL: {e}")
            return url

    def _parse_s3_url(self, url: str) -> tuple:
        """
        Parse an S3 URL to extract bucket name and key.

        Handles various S3 URL formats:
        - https://bucket.s3.amazonaws.com/key
        - https://bucket.s3.region.amazonaws.com/key
        - https://s3.amazonaws.com/bucket/key
        - CloudFront URL with known path pattern
        """
        parsed = urlparse(url)

        # Try to extract from CloudFront URL (assume same key structure)
        if self._is_cloudfront_url(url):
            # CloudFront URLs use the same key as S3
            # Path starts with / so remove it
            key = parsed.path.lstrip('/')
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
            return bucket, key

        # S3 virtual-hosted style: bucket.s3.amazonaws.com
        host = parsed.netloc
        if '.s3.' in host or host.endswith('.s3.amazonaws.com'):
            bucket = host.split('.s3')[0]
            key = parsed.path.lstrip('/')
            return bucket, key

        # S3 path style: s3.amazonaws.com/bucket/key
        if 's3.amazonaws.com' in host:
            parts = parsed.path.lstrip('/').split('/', 1)
            if len(parts) == 2:
                return parts[0], parts[1]

        # Use configured bucket name as fallback
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        key = parsed.path.lstrip('/')
        return bucket, key


# Singleton instance for convenience
_video_service = None


def get_video_service() -> VideoURLService:
    """Get or create the video service singleton."""
    global _video_service
    if _video_service is None:
        _video_service = VideoURLService()
    return _video_service


def generate_signed_video_url(
    video_url: str,
    expiration_seconds: int = DEFAULT_URL_EXPIRATION
) -> str:
    """
    Convenience function to generate a signed video URL.

    Args:
        video_url: The original video URL
        expiration_seconds: How long the URL should be valid (default: 4 hours)

    Returns:
        A signed URL that expires after the specified time
    """
    service = get_video_service()
    return service.generate_signed_url(video_url, expiration_seconds)
