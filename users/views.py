import requests
from django.conf import settings
from django.http import JsonResponse
from django.views import View

class CognitoCallbackView(View):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return JsonResponse({"error": "No code provided"}, status=400)

        token_url = f"https://{settings.COGNITO_DOMAIN}/oauth2/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.COGNITO_CLIENT_ID,
            "code": code,
            "redirect_uri": settings.COGNITO_REDIRECT_URI
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(token_url, data=data, headers=headers)
        if response.status_code == 200:
            tokens = response.json()
            return JsonResponse(tokens)  # You can redirect or store tokens
        else:
            return JsonResponse({"error": "Failed to get token"}, status=500)


# Create your views here.
