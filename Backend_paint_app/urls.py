from django.urls import path
from .views import LoginStep1View, VerifyTelegramCodeView, SetTelegramIDView, get_user_profile, \
    server_info, LogView, check_auth, create_request, get_requests, update_status
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView

urlpatterns = [
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/login-step-1/', LoginStep1View.as_view()),
    path('auth/verify-code/', VerifyTelegramCodeView.as_view()),
    path('auth/set-telegram-id/', SetTelegramIDView.as_view()),
    path('check-auth/', check_auth), # Проверка авторизации
    path('auth/me/', get_user_profile), # Получение информации о пользователе
    path('server-info/', server_info, name='server_info'), # Получение информации о сервере
    path('logs/', LogView.as_view(), name='logs'), # Получение логов
    path('requests/', create_request, name='create-request'), # Добавление заявки
    path('requests-list/', get_requests, name='request-list'), # Возвращает заявки
    path("requests/<int:request_id>/", update_status, name="update_status"), # Изменения статуса заявки
]
