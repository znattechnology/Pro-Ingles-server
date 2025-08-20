# Google OAuth Implementation - Tuwi Backend

## Overview

This document describes the Google OAuth 2.0 implementation for the Tuwi Beauty Platform backend. The implementation provides secure authentication using Google accounts, allowing users to sign in without creating separate passwords.

## Architecture

### Components

1. **GoogleOAuthService** (`apps/users/services.py`) - Core OAuth business logic
2. **OAuth Serializers** (`apps/users/serializers.py`) - Request/response validation
3. **OAuth Views** (`apps/users/views.py`) - API endpoints
4. **OAuth URLs** (`apps/users/urls.py`) - URL routing

### Flow Diagram

```
Frontend → Google OAuth URL → Google Authorization → Authorization Code → Backend → JWT Tokens
```

## Configuration

### Environment Variables

```bash
# Required for production
GOOGLE_OAUTH2_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_google_client_secret
GOOGLE_OAUTH2_REDIRECT_URI=http://localhost:3000/auth/google/callback

# Optional - defaults provided
FRONTEND_URL=http://localhost:3000
```

### Django Settings

The OAuth configuration is automatically loaded from environment variables in `core/settings.py`:

```python
OAUTH2_SETTINGS = {
    'GOOGLE': {
        'CLIENT_ID': GOOGLE_OAUTH2_CLIENT_ID,
        'CLIENT_SECRET': GOOGLE_OAUTH2_CLIENT_SECRET,
        'REDIRECT_URI': GOOGLE_OAUTH2_REDIRECT_URI,
        'SCOPE': [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ],
        'AUTH_URI': 'https://accounts.google.com/o/oauth2/auth',
        'TOKEN_URI': 'https://oauth2.googleapis.com/token',
        'USER_INFO_URI': 'https://www.googleapis.com/oauth2/v2/userinfo',
    }
}
```

## API Endpoints

### 1. Generate OAuth URL

**Endpoint:** `POST /api/v1/users/oauth/google/url/`

**Description:** Generates a Google OAuth authorization URL that the frontend can redirect users to.

**Request:**
```json
{
    "redirect_uri": "http://localhost:3000/auth/google/callback",  // Optional
    "state": "random_state_string"  // Optional, auto-generated if not provided
}
```

**Response:**
```json
{
    "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&scope=...&response_type=code&access_type=offline&prompt=consent&state=..."
}
```

**Error Response:**
```json
{
    "error": "Failed to generate OAuth URL: Google OAuth client ID not configured"
}
```

### 2. OAuth Login

**Endpoint:** `POST /api/v1/users/oauth/google/login/`

**Description:** Authenticates a user using Google OAuth and returns JWT tokens.

**Request (Option 1 - Authorization Code):**
```json
{
    "code": "4/0AX4XfWj..."  // Authorization code from Google
}
```

**Request (Option 2 - Access Token):**
```json
{
    "access_token": "ya29.a0ARrdaM..."  // Access token from Google
}
```

**Request (Option 3 - ID Token):**
```json
{
    "id_token": "eyJhbGciOiJSUzI1NiIs..."  // ID token from Google
}
```

**Success Response:**
```json
{
    "message": "Login successful",
    "user": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@example.com",
        "name": "John Doe",
        "role": "customer",
        "avatar": null,
        "email_verified": true,
        "google_id": "1234567890"
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

**Error Response:**
```json
{
    "error": "Authentication failed: Invalid authorization code"
}
```

## Frontend Integration

### Example JavaScript Implementation

```javascript
// 1. Get OAuth URL
const getGoogleOAuthURL = async () => {
    const response = await fetch('/api/v1/users/oauth/google/url/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            redirect_uri: 'http://localhost:3000/auth/google/callback',
            state: generateRandomState()
        })
    });
    
    const data = await response.json();
    return data.auth_url;
};

// 2. Redirect user to Google
const initiateGoogleLogin = async () => {
    const authUrl = await getGoogleOAuthURL();
    window.location.href = authUrl;
};

// 3. Handle callback (in your callback page)
const handleGoogleCallback = async (code, state) => {
    // Verify state parameter for security
    if (state !== getStoredState()) {
        throw new Error('Invalid state parameter');
    }
    
    const response = await fetch('/api/v1/users/oauth/google/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code })
    });
    
    const data = await response.json();
    
    if (response.ok) {
        // Store tokens
        localStorage.setItem('accessToken', data.tokens.access);
        localStorage.setItem('refreshToken', data.tokens.refresh);
        
        // Store user data
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redirect to dashboard
        window.location.href = '/dashboard';
    } else {
        console.error('Login failed:', data.error);
    }
};
```

### React Hook Example

```typescript
import { useState } from 'react';

interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    avatar?: string;
    email_verified: boolean;
    google_id: string;
}

interface Tokens {
    access: string;
    refresh: string;
}

export const useGoogleAuth = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const initiateGoogleLogin = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/v1/users/oauth/google/url/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    redirect_uri: `${window.location.origin}/auth/google/callback`
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                window.location.href = data.auth_url;
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('Failed to initiate Google login');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleCallback = async (code: string): Promise<{ user: User; tokens: Tokens } | null> => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/v1/users/oauth/google/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });

            const data = await response.json();
            
            if (response.ok) {
                return { user: data.user, tokens: data.tokens };
            } else {
                setError(data.error);
                return null;
            }
        } catch (err) {
            setError('Failed to complete Google login');
            return null;
        } finally {
            setLoading(false);
        }
    };

    return {
        initiateGoogleLogin,
        handleGoogleCallback,
        loading,
        error
    };
};
```

## Security Features

### 1. State Parameter Validation
- Automatic generation of secure state parameter
- Frontend should verify state parameter matches

### 2. Token Verification
- ID tokens are verified using Google's public keys
- Access tokens are validated against Google's API

### 3. User Account Linking
- Existing users are linked by email address
- New users are created automatically
- Google ID is stored for future reference

### 4. Secure Token Storage
- JWT tokens are generated using Django's secret key
- Refresh tokens are rotated on each use
- Tokens include user information in claims

## User Model Integration

The OAuth implementation automatically handles:

1. **New Users:** Creates new user accounts with:
   - Email from Google
   - Name from Google profile
   - `google_id` field populated
   - `email_verified` set to true
   - Default role: 'customer'

2. **Existing Users:** Updates existing accounts with:
   - Links Google ID if not already linked
   - Updates name if empty
   - Marks email as verified
   - Preserves existing user data

## Error Handling

Common error scenarios and responses:

| Error | HTTP Status | Description |
|-------|-------------|-------------|
| Missing OAuth credentials | 400 | Client ID/Secret not configured |
| Invalid authorization code | 400 | Code expired or invalid |
| Invalid access token | 400 | Token expired or malformed |
| Invalid ID token | 400 | Token verification failed |
| Google API error | 400 | Google service unavailable |
| User creation failed | 500 | Database error |

## Testing

### Manual Testing

1. **Test OAuth URL Generation:**
```bash
curl -X POST http://localhost:8000/api/v1/users/oauth/google/url/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

2. **Test OAuth Login (with test data):**
```bash
curl -X POST http://localhost:8000/api/v1/users/oauth/google/login/ \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
```

### Automated Testing

Run the included test script:
```bash
python test_oauth.py
```

## Production Deployment

### 1. Google Cloud Console Setup
1. Create a new project or select existing project
2. Enable Google+ API and Google OAuth2 API
3. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: Your frontend callback URL
4. Note the Client ID and Client Secret

### 2. Environment Configuration
```bash
# Production environment variables
GOOGLE_OAUTH2_CLIENT_ID=your_actual_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_actual_client_secret
GOOGLE_OAUTH2_REDIRECT_URI=https://yourdomain.com/auth/google/callback
FRONTEND_URL=https://yourdomain.com
```

### 3. Security Considerations
- Use HTTPS in production
- Implement CORS properly
- Monitor OAuth usage and errors
- Regularly rotate client secrets
- Implement rate limiting on OAuth endpoints

## Monitoring and Analytics

The implementation includes logging for:
- OAuth authentication attempts
- User creation/linking events
- Authentication errors
- Performance metrics

Log entries can be found in:
- Django application logs
- User activity tracking (apps/analytics)
- System performance metrics

## Support and Troubleshooting

### Common Issues

1. **"Client ID not configured"**
   - Ensure GOOGLE_OAUTH2_CLIENT_ID is set in environment
   - Verify environment variables are loaded correctly

2. **"Invalid redirect URI"**
   - Check Google Console redirect URI configuration
   - Ensure frontend callback URL matches exactly

3. **"Invalid authorization code"**
   - Code may have expired (10 minutes lifetime)
   - Code may have been used already (single use)
   - Check if code is being sent correctly from frontend

4. **"Authentication failed"**
   - Check Google API quota limits
   - Verify Google APIs are enabled in console
   - Check network connectivity to Google services

### Debug Mode

Set Django DEBUG=True to see detailed error messages and stack traces.