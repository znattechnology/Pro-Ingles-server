"""
Integration services for external APIs and services.
"""

import json
import time
import hashlib
import hmac
import requests
from typing import Dict, Any, Optional, List
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.mail import send_mail
import logging

from .models import (
    IntegrationProvider, IntegrationLog, APIQuota, 
    FileUpload, LocationData, SocialAuthProfile
)

logger = logging.getLogger(__name__)


class BaseIntegrationService:
    """Base class for all integration services."""
    
    def __init__(self, provider_name: str):
        try:
            self.provider = IntegrationProvider.objects.get(
                name=provider_name, status='active'
            )
        except IntegrationProvider.DoesNotExist:
            raise ValueError(f"Provider '{provider_name}' not found or inactive")
    
    def log_request(self, endpoint: str, method: str, request_data: Dict = None, 
                   user=None, correlation_id=None):
        """Log API request."""
        return IntegrationLog.objects.create(
            provider=self.provider,
            log_type='request',
            status='info',
            endpoint=endpoint,
            method=method,
            request_data=request_data,
            user=user,
            correlation_id=correlation_id
        )
    
    def log_response(self, log_entry: IntegrationLog, response_data: Dict = None,
                    status_code: int = None, response_time: float = None,
                    error_message: str = None):
        """Log API response."""
        status = 'success' if status_code and 200 <= status_code < 300 else 'error'
        
        IntegrationLog.objects.create(
            provider=self.provider,
            log_type='response',
            status=status,
            endpoint=log_entry.endpoint,
            method=log_entry.method,
            response_data=response_data,
            status_code=status_code,
            response_time=response_time,
            error_message=error_message,
            user=log_entry.user,
            correlation_id=log_entry.correlation_id
        )
        
        # Update provider counters
        if status == 'success':
            self.provider.increment_success()
        else:
            self.provider.increment_error()
    
    def check_quota(self, quota_type: str, amount: int = 1) -> bool:
        """Check if quota allows the operation."""
        try:
            quota = self.provider.quotas.get(quota_type=quota_type)
            return not quota.is_over_limit()
        except APIQuota.DoesNotExist:
            return True  # No quota set, allow operation
    
    def increment_quota(self, quota_type: str, amount: int = 1):
        """Increment quota usage."""
        try:
            quota = self.provider.quotas.get(quota_type=quota_type)
            quota.increment_usage(amount)
        except APIQuota.DoesNotExist:
            pass  # No quota set, ignore
    
    def make_request(self, endpoint: str, method: str = 'GET', 
                    data: Dict = None, headers: Dict = None,
                    user=None, correlation_id=None) -> requests.Response:
        """Make authenticated API request."""
        # Check quota
        if not self.check_quota('requests'):
            raise Exception("API quota exceeded")
        
        # Log request
        log_entry = self.log_request(endpoint, method, data, user, correlation_id)
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TuwiBeauty/1.0'
        }
        if headers:
            request_headers.update(headers)
        
        # Add authentication
        auth_headers = self.get_auth_headers()
        request_headers.update(auth_headers)
        
        # Make request
        url = self.provider.base_url.rstrip('/') + '/' + endpoint.lstrip('/')
        start_time = time.time()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data if method in ['POST', 'PUT', 'PATCH'] else None,
                params=data if method == 'GET' else None,
                headers=request_headers,
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            # Log response
            try:
                response_data = response.json()
            except:
                response_data = {'raw_response': response.text}
            
            self.log_response(
                log_entry, response_data, response.status_code, 
                response_time
            )
            
            # Increment quota
            self.increment_quota('requests')
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            self.log_response(
                log_entry, None, None, response_time, str(e)
            )
            raise
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers. Override in subclasses."""
        headers = {}
        
        if self.provider.api_key:
            headers['Authorization'] = f'Bearer {self.provider.api_key}'
        
        return headers


class GoogleMapsService(BaseIntegrationService):
    """Google Maps API integration."""
    
    def __init__(self):
        super().__init__('google_maps')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Google Maps uses API key in URL params."""
        return {}
    
    def geocode_address(self, address: str, user=None) -> Optional[LocationData]:
        """Geocode an address to coordinates."""
        try:
            params = {
                'address': address,
                'key': self.provider.api_key
            }
            
            response = self.make_request(
                'geocode/json', 'GET', params, user=user
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    result = data['results'][0]
                    geometry = result['geometry']['location']
                    
                    # Parse address components
                    components = {}
                    for component in result.get('address_components', []):
                        for addr_type in component['types']:
                            components[addr_type] = component['long_name']
                    
                    # Create or update location data
                    location_data = LocationData.objects.create(
                        location_type='address',
                        name=result.get('formatted_address', ''),
                        street_address=components.get('street_number', '') + ' ' + components.get('route', ''),
                        city=components.get('locality', ''),
                        state=components.get('administrative_area_level_1', ''),
                        postal_code=components.get('postal_code', ''),
                        country=components.get('country', ''),
                        latitude=geometry['lat'],
                        longitude=geometry['lng'],
                        provider=self.provider,
                        external_place_id=result.get('place_id', ''),
                        formatted_address=result['formatted_address'],
                        place_data=result
                    )
                    
                    return location_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding address '{address}': {str(e)}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float, user=None) -> Optional[LocationData]:
        """Reverse geocode coordinates to address."""
        try:
            params = {
                'latlng': f'{latitude},{longitude}',
                'key': self.provider.api_key
            }
            
            response = self.make_request(
                'geocode/json', 'GET', params, user=user
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    result = data['results'][0]
                    
                    # Parse address components
                    components = {}
                    for component in result.get('address_components', []):
                        for addr_type in component['types']:
                            components[addr_type] = component['long_name']
                    
                    location_data = LocationData.objects.create(
                        location_type='coordinates',
                        name=result.get('formatted_address', ''),
                        street_address=components.get('street_number', '') + ' ' + components.get('route', ''),
                        city=components.get('locality', ''),
                        state=components.get('administrative_area_level_1', ''),
                        postal_code=components.get('postal_code', ''),
                        country=components.get('country', ''),
                        latitude=latitude,
                        longitude=longitude,
                        provider=self.provider,
                        external_place_id=result.get('place_id', ''),
                        formatted_address=result['formatted_address'],
                        place_data=result
                    )
                    
                    return location_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error reverse geocoding coordinates {latitude}, {longitude}: {str(e)}")
            return None


class TwilioSMSService(BaseIntegrationService):
    """Twilio SMS integration."""
    
    def __init__(self):
        super().__init__('twilio')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Twilio uses Basic Auth."""
        import base64
        
        auth_string = f"{self.provider.api_key}:{self.provider.api_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            'Authorization': f'Basic {encoded_auth}'
        }
    
    def send_sms(self, to_phone: str, message: str, from_phone: str = None, user=None) -> bool:
        """Send SMS message."""
        try:
            # Check quota
            if not self.check_quota('sms'):
                logger.warning(f"SMS quota exceeded for provider {self.provider.name}")
                return False
            
            config = self.provider.get_config_dict()
            from_phone = from_phone or config.get('default_from_phone')
            
            if not from_phone:
                logger.error("No from_phone number configured for Twilio")
                return False
            
            data = {
                'From': from_phone,
                'To': to_phone,
                'Body': message
            }
            
            # Get account SID from config
            account_sid = config.get('account_sid')
            if not account_sid:
                logger.error("No account_sid configured for Twilio")
                return False
            
            endpoint = f'Accounts/{account_sid}/Messages.json'
            
            response = self.make_request(
                endpoint, 'POST', data, user=user
            )
            
            if response.status_code == 201:
                # Increment SMS quota
                self.increment_quota('sms')
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_phone}: {str(e)}")
            return False
    
    def send_verification_code(self, phone_number: str, user=None) -> Optional[str]:
        """Send verification code via SMS."""
        import random
        import string
        
        # Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        message = f"Seu código de verificação Tuwi Beauty é: {code}. Válido por 10 minutos."
        
        if self.send_sms(phone_number, message, user=user):
            return code
        
        return None


class CloudinaryService(BaseIntegrationService):
    """Cloudinary image upload and management."""
    
    def __init__(self):
        super().__init__('cloudinary')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Cloudinary uses signature-based auth."""
        return {}
    
    def upload_image(self, file_data, filename: str, user=None, 
                    folder: str = 'tuwi') -> Optional[FileUpload]:
        """Upload image to Cloudinary."""
        try:
            import cloudinary
            import cloudinary.uploader
            
            config = self.provider.get_config_dict()
            
            # Configure Cloudinary
            cloudinary.config(
                cloud_name=config.get('cloud_name'),
                api_key=self.provider.api_key,
                api_secret=self.provider.api_secret
            )
            
            # Create file upload record
            file_upload = FileUpload.objects.create(
                provider=self.provider,
                user=user,
                original_filename=filename,
                file_type='image',
                file_size=len(file_data),
                mime_type='image/jpeg',  # Default, should be detected
                external_id='',
                storage_path=f"{folder}/{filename}",
                status='uploading'
            )
            
            try:
                # Upload to Cloudinary
                result = cloudinary.uploader.upload(
                    file_data,
                    folder=folder,
                    public_id=f"{user.id}_{int(time.time())}_{filename}",
                    resource_type="auto"
                )
                
                # Update file upload record
                file_upload.external_id = result['public_id']
                file_upload.public_url = result['secure_url']
                file_upload.metadata = {
                    'width': result.get('width'),
                    'height': result.get('height'),
                    'format': result.get('format'),
                    'bytes': result.get('bytes'),
                    'version': result.get('version')
                }
                file_upload.mark_completed(result['secure_url'])
                
                # Log successful upload
                self.log_request(
                    'upload', 'POST', 
                    {'filename': filename, 'folder': folder},
                    user=user
                )
                
                # Increment storage quota
                self.increment_quota('storage', len(file_data))
                
                return file_upload
                
            except Exception as e:
                file_upload.mark_failed(str(e))
                raise
            
        except Exception as e:
            logger.error(f"Error uploading image {filename}: {str(e)}")
            return None
    
    def delete_image(self, public_id: str, user=None) -> bool:
        """Delete image from Cloudinary."""
        try:
            import cloudinary
            import cloudinary.uploader
            
            config = self.provider.get_config_dict()
            
            cloudinary.config(
                cloud_name=config.get('cloud_name'),
                api_key=self.provider.api_key,
                api_secret=self.provider.api_secret
            )
            
            result = cloudinary.uploader.destroy(public_id)
            
            if result.get('result') == 'ok':
                # Update file upload record
                try:
                    file_upload = FileUpload.objects.get(
                        external_id=public_id,
                        provider=self.provider
                    )
                    file_upload.status = 'deleted'
                    file_upload.save()
                except FileUpload.DoesNotExist:
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting image {public_id}: {str(e)}")
            return False


class MailchimpService(BaseIntegrationService):
    """Mailchimp email marketing integration."""
    
    def __init__(self):
        super().__init__('mailchimp')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Mailchimp uses API key in Authorization header."""
        return {
            'Authorization': f'Bearer {self.provider.api_key}'
        }
    
    def add_subscriber(self, email: str, first_name: str = '', 
                      last_name: str = '', tags: List[str] = None,
                      user=None) -> bool:
        """Add subscriber to Mailchimp list."""
        try:
            config = self.provider.get_config_dict()
            list_id = config.get('default_list_id')
            
            if not list_id:
                logger.error("No default_list_id configured for Mailchimp")
                return False
            
            data = {
                'email_address': email,
                'status': 'subscribed',
                'merge_fields': {
                    'FNAME': first_name,
                    'LNAME': last_name
                }
            }
            
            if tags:
                data['tags'] = tags
            
            endpoint = f'lists/{list_id}/members'
            
            response = self.make_request(
                endpoint, 'POST', data, user=user
            )
            
            if response.status_code in [200, 201]:
                # Increment email quota
                self.increment_quota('emails')
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding subscriber {email}: {str(e)}")
            return False
    
    def remove_subscriber(self, email: str, user=None) -> bool:
        """Remove subscriber from Mailchimp list."""
        try:
            config = self.provider.get_config_dict()
            list_id = config.get('default_list_id')
            
            if not list_id:
                return False
            
            # Hash email for Mailchimp API
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()
            
            endpoint = f'lists/{list_id}/members/{email_hash}'
            
            response = self.make_request(
                endpoint, 'DELETE', user=user
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error removing subscriber {email}: {str(e)}")
            return False


class GoogleAuthService(BaseIntegrationService):
    """Google OAuth integration."""
    
    def __init__(self):
        super().__init__('google_oauth')
    
    def exchange_code_for_token(self, authorization_code: str, 
                               redirect_uri: str) -> Optional[Dict]:
        """Exchange authorization code for access token."""
        try:
            config = self.provider.get_config_dict()
            
            data = {
                'client_id': self.provider.api_key,
                'client_secret': self.provider.api_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            
            response = self.make_request(
                'token', 'POST', data
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            return None
    
    def get_user_profile(self, access_token: str) -> Optional[Dict]:
        """Get user profile from Google."""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = self.make_request(
                'userinfo', 'GET', headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    def create_or_update_social_profile(self, user, token_data: Dict, 
                                      profile_data: Dict) -> SocialAuthProfile:
        """Create or update social auth profile."""
        profile, created = SocialAuthProfile.objects.update_or_create(
            user=user,
            provider='google',
            defaults={
                'social_id': profile_data['id'],
                'email': profile_data.get('email', ''),
                'full_name': profile_data.get('name', ''),
                'avatar_url': profile_data.get('picture', ''),
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', ''),
                'token_expires_at': timezone.now() + timedelta(
                    seconds=token_data.get('expires_in', 3600)
                ),
                'profile_data': profile_data,
                'is_verified': profile_data.get('verified_email', False)
            }
        )
        
        profile.update_last_login()
        return profile


class WebhookService:
    """Service for handling webhooks."""
    
    @staticmethod
    def trigger_webhook(event_type: str, data: Dict, user=None):
        """Trigger webhooks for a specific event type."""
        from .models import Webhook
        
        webhooks = Webhook.objects.filter(
            event_type=event_type,
            status='active'
        )
        
        for webhook in webhooks:
            try:
                WebhookService._send_webhook(webhook, data, user)
            except Exception as e:
                logger.error(f"Error sending webhook {webhook.id}: {str(e)}")
                webhook.increment_failure()
    
    @staticmethod
    def _send_webhook(webhook, data: Dict, user=None):
        """Send individual webhook."""
        import uuid
        
        # Prepare payload
        payload = {
            'event_type': webhook.event_type,
            'timestamp': timezone.now().isoformat(),
            'data': data,
            'webhook_id': str(webhook.id)
        }
        
        # Add signature if secret key is set
        headers = webhook.headers.copy()
        if webhook.secret_key:
            signature = WebhookService._generate_signature(
                json.dumps(payload), webhook.secret_key
            )
            headers['X-Webhook-Signature'] = signature
        
        # Send webhook
        response = requests.post(
            webhook.url,
            json=payload,
            headers=headers,
            timeout=webhook.timeout
        )
        
        if response.status_code == 200:
            webhook.increment_success()
        else:
            webhook.increment_failure()
            
        # Log webhook
        IntegrationLog.objects.create(
            provider=webhook.provider,
            log_type='webhook',
            status='success' if response.status_code == 200 else 'error',
            endpoint=webhook.url,
            method='POST',
            request_data=payload,
            response_data={'status_code': response.status_code},
            status_code=response.status_code,
            user=user
        )
    
    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"


# Convenience functions for easy access
def send_sms(to_phone: str, message: str, user=None) -> bool:
    """Send SMS using configured SMS provider."""
    try:
        sms_service = TwilioSMSService()
        return sms_service.send_sms(to_phone, message, user=user)
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False


def geocode_address(address: str, user=None) -> Optional[LocationData]:
    """Geocode address using configured maps provider."""
    try:
        maps_service = GoogleMapsService()
        return maps_service.geocode_address(address, user=user)
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return None


def upload_image(file_data, filename: str, user=None) -> Optional[FileUpload]:
    """Upload image using configured storage provider."""
    try:
        storage_service = CloudinaryService()
        return storage_service.upload_image(file_data, filename, user=user)
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return None


def add_email_subscriber(email: str, first_name: str = '', 
                        last_name: str = '', user=None) -> bool:
    """Add email subscriber using configured email provider."""
    try:
        email_service = MailchimpService()
        return email_service.add_subscriber(email, first_name, last_name, user=user)
    except Exception as e:
        logger.error(f"Error adding email subscriber: {str(e)}")
        return False