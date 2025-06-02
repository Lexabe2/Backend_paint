from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
import requests
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import os
from rest_framework import generics
from .models import Request
from .serializers import RequestSerializer
import platform
import socket
from django.http import JsonResponse
from .utils.logger import get_logger, log_request_info
from django.conf import settings

logger = get_logger('user')  # или 'app', 'django' и т.д.
logger_app = get_logger('app')

BOT_TOKEN = os.getenv("BOT_TOKEN")


class LoginStep1View(APIView):
    def post(self, request):
        _ = self
        username = request.data.get('username')
        password = request.data.get('password')

        log_request_info(logger, request, 'Попытка входа', level='info')

        user = authenticate(request, username=username, password=password)

        if user:
            log_request_info(logger, request, 'Пользователь вошел', level='info')
            token = str(RefreshToken.for_user(user).access_token)

            if user.telegram_id:
                code = user.generate_telegram_code()
                log_request_info(logger, request, f'Сгенерирован код Telegram {code}', level='info')
                try:
                    response = requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        data={
                            'chat_id': user.telegram_id,
                            'text': f'Ваш код подтверждения:\n`{code}`',
                            'parse_mode': 'Markdown'
                        }
                    )
                    response.raise_for_status()
                    log_request_info(logger, request, 'Код отправлен в Telegram', level='info')
                except requests.RequestException as e:
                    log_request_info(logger, request, f'Ошибка при отправке кода в Telegram: {e}', level='error')

                return Response({'token': token, 'has_telegram_id': True}, status=200)
            else:
                log_request_info(logger, request, f'Telegram ID не найден для {username}', level='error')
                return Response({'token': token, 'has_telegram_id': False}, status=200)
        log_request_info(logger, request, 'Неудачная попытка входа', level='warning')
        return Response({'detail': 'Неверные данные'}, status=400)


class VerifyTelegramCodeView(APIView):
    def post(self, request):
        _ = self
        username = request.data.get('username')
        code = request.data.get('code')

        log_request_info(logger, request, "Запрос проверки кода Telegram")

        try:
            user = CustomUser.objects.get(username=username)
            if user.telegram_code == code:
                log_request_info(logger, request, "Код подтвержден")
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
            else:
                log_request_info(logger, request, "Неверный код Telegram", level='warning')
                return Response({'detail': 'Неверный код'}, status=400)

        except CustomUser.DoesNotExist:
            log_request_info(logger, request, "Пользователь не найден", level='error')
            return Response({'detail': 'Пользователь не найден'}, status=404)

        except CustomUser.DoesNotExist:
            log_request_info(logger, request, 'Проблемы', level='error')
            return Response({'detail': 'Пользователь не найден'}, status=404)


class SetTelegramIDView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _ = self
        telegram_id = request.data.get('telegram_id')
        user = request.user
        user.telegram_id = telegram_id
        user.save()

        # Отправка кода сразу
        code = user.generate_telegram_code()
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                'chat_id': telegram_id,
                'text': f'Ваш код подтверждения: {code}'
            }
        )

        return Response({'detail': 'Telegram ID добавлен и код отправлен'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    log_request_info(logger_app, request, 'Отработала get_user_profile', level='info')
    return Response({
        "full_name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "role": user.role
    })


def server_info(request):
    info = {
        'hostname': socket.gethostname(),
        'ip_address': socket.gethostbyname(socket.gethostname()),
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'server_software': request.META.get('SERVER_SOFTWARE', 'Unknown'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
    }
    log_request_info(logger_app, request, 'Отработала server_info', level='info')
    return JsonResponse(info)


class RequestCreateAPIView(generics.CreateAPIView):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer


class LogView(APIView):
    def get(self, request):
        _ = self
        log_file_path = os.path.join(settings.BASE_DIR, 'logs/django.log')
        if not os.path.exists(log_file_path):
            return Response({'logs': ['Лог-файл не найден']}, status=404)

        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-100:]  # последние 100 строк
            log_request_info(logger_app, request, 'Пользователь просматривает логи', level='info')
            return Response({'logs': lines})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
