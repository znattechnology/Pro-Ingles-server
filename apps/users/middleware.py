"""
JWT Cookie Authentication Middleware

This middleware enables authentication via HttpOnly cookies as a fallback
when the Authorization header is not present. It provides:

1. XSS Protection: Tokens stored in HttpOnly cookies cannot be accessed by JavaScript
2. Backward Compatibility: Still supports Authorization header authentication
3. Automatic Token Injection: Adds Authorization header from cookie for DRF compatibility

Security Notes:
- HttpOnly cookies are immune to XSS attacks
- SameSite=Lax provides CSRF protection for most cases
- Secure flag ensures cookies are only sent over HTTPS in production
"""

from django.utils.deprecation import MiddlewareMixin


class JWTCookieAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware that reads JWT tokens from HttpOnly cookies and adds them
    to the request's Authorization header if not already present.

    This allows DRF's JWTAuthentication to work seamlessly with cookie-based auth.

    Flow:
    1. Check if Authorization header exists
    2. If not, check for access_token cookie
    3. If cookie exists, add it as Bearer token in Authorization header
    4. DRF's JWTAuthentication handles the rest
    """

    def process_request(self, request):
        import logging
        logger = logging.getLogger(__name__)

        # Skip if Authorization header already exists
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header:
            logger.debug(f"Auth header already present for {request.path}")
            return None

        # Try to get access token from HttpOnly cookie
        access_token = request.COOKIES.get('access_token')

        # Debug logging for vapi endpoints
        if 'vapi' in request.path:
            logger.info(f"[JWT Cookie] Path: {request.path}")
            logger.info(f"[JWT Cookie] Cookies received: {list(request.COOKIES.keys())}")
            logger.info(f"[JWT Cookie] access_token cookie present: {bool(access_token)}")

        if access_token:
            # Inject the token into the Authorization header
            # This allows DRF's JWTAuthentication to process it normally
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
            if 'vapi' in request.path:
                logger.info(f"[JWT Cookie] Token injected into Authorization header")

        return None
