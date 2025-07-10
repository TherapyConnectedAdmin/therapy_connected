import json, requests
from jose import jwt
from django.conf import settings
from users.models import User

COGNITO_JWKS_URL = f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"

def get_token_from_header(request):
    auth = request.headers.get("Authorization", "")
    return auth.replace("Bearer ", "")

class CognitoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = get_token_from_header(request)
        if token:
            try:
                jwks = requests.get(COGNITO_JWKS_URL).json()
                claims = jwt.decode(token, jwks, algorithms=["RS256"], audience=settings.COGNITO_CLIENT_ID)

                # Auto-create local User object
                user, _ = User.objects.get_or_create(
                    email=claims["email"],
                    defaults={
                        "name": claims.get("name"),
                        "role": claims.get("custom:role"),
                        "practice_id": claims.get("custom:practice_id"),
                        "invited_by": claims.get("custom:invited_by"),
                    },
                )
                request.user = user
            except Exception as e:
                request.user = None  # Optional fallback

        return self.get_response(request)
