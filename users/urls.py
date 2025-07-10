from django.urls import path
from .views import CognitoCallbackView

urlpatterns = [
    path('cognito/callback/', CognitoCallbackView.as_view(), name='cognito_callback'),
]
