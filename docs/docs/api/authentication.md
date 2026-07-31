---
sidebar_position: 1
title: Authentication
description: API authentication guide
---

# Authentication

ML Pipeline uses JWT (JSON Web Tokens) for API authentication.

## Getting a Token

### Register

```bash
POST /api/v1/auth/register
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "Full Name"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "role": "user"
  }
}
```

### Login

```bash
POST /api/v1/auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "role": "user"
  }
}
```

## Using the Token

Include the token in the `Authorization` header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Example with cURL

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example with Python

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
response = requests.get("http://localhost:8000/api/v1/auth/me", headers=headers)
```

### Example with JavaScript

```javascript
const response = await fetch("http://localhost:8000/api/v1/auth/me", {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});
```

## API Keys

For server-to-server authentication, use API keys.

### Generate API Key

```bash
POST /api/v1/auth/api-key
Authorization: Bearer YOUR_TOKEN
```

**Response:**

```json
{
  "api_key": "mlp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "API key generated successfully"
}
```

### Use API Key

```bash
X-API-Key: mlp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## User Roles

| Role | Description |
|------|-------------|
| `admin` | Full access to all features |
| `data_scientist` | Can create, train, and deploy models |
| `user` | Can view and use models |

### Role-Based Access Control

```python
from app.core.security import require_role, UserRole

# Require specific role
@router.get("/admin-only")
async def admin_endpoint(user = Depends(require_role(UserRole.ADMIN))):
    return {"message": "Admin only"}

# Require multiple roles
@router.get("/data-science")
async def ds_endpoint(user = Depends(require_role(UserRole.ADMIN, UserRole.DATA_SCIENTIST))):
    return {"message": "Data scientists and admins"}
```

## Token Expiry

By default, tokens expire after 7 days (10080 minutes).

To refresh, simply login again to get a new token.

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions"
}
```

## Security Best Practices

1. **Store tokens securely** - Use secure storage (not localStorage in production)
2. **Don't expose tokens** - Never log or expose tokens in URLs
3. **Use HTTPS** - Always use HTTPS in production
4. **Rotate API keys** - Regularly rotate API keys
5. **Implement token refresh** - Use short-lived access tokens with refresh tokens

## Next Steps

- [Datasets API](./datasets)
- [Models API](./models)
- [Predictions API](./predictions)
