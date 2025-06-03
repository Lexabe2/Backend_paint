from django.urls import path
from .views import LoginStep1View, VerifyTelegramCodeView, SetTelegramIDView, get_user_profile, RequestCreateAPIView, \
    server_info, LogView, check_auth
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView

urlpatterns = [
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/login-step-1/', LoginStep1View.as_view()),
    path('auth/verify-code/', VerifyTelegramCodeView.as_view()),
    path('auth/set-telegram-id/', SetTelegramIDView.as_view()),
    path('check-auth/', check_auth),
    path('auth/me/', get_user_profile),
    path('requests/', RequestCreateAPIView.as_view(), name='create-request'),
    path('server-info/', server_info, name='server_info'),
    path('logs/', LogView.as_view(), name='logs'),
]
