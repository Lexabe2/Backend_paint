from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, ATM
import requests
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import os
from .models import Request
import platform
import socket
from django.http import JsonResponse
from .utils.logger import get_logger, log_request_info
from django.conf import settings
from datetime import datetime
import json
from django.utils import timezone

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
def check_auth(request):
    return Response({'status': 'ok'})


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_request(request):
    if request.method != 'POST':
        log_request_info(logger_app, request, 'Неправильный метод запроса', level='error')
        return JsonResponse({'error': 'Только POST'}, status=405)

    try:
        data = json.loads(request.body)

        required_fields = ['project', 'device', 'quantity', 'date_received', 'deadline']
        if not all(field in data for field in required_fields):
            log_request_info(logger_app, request, 'Не все поля заполнены', level='error')
            return JsonResponse({'error': 'Не все поля заполнены'}, status=400)

        new_request = Request(
            project=data['project'],
            device=data['device'],
            quantity=int(data['quantity']),
            date_received=datetime.strptime(data['date_received'], '%Y-%m-%d').date(),
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date(),
            status='Создана'
        )
        log_request_info(logger_app, request, f'Заявка создана {data}', level='info')
        new_request.save()

        return JsonResponse({
            'id': new_request.id,
            'request_id': new_request.request_id,
            'project': new_request.project,
            'device': new_request.device,
            'quantity': new_request.quantity,
            'date_received': new_request.date_received,
            'deadline': new_request.deadline
        }, status=201)

    except Exception as e:
        log_request_info(logger_app, request, f'Ошибка {str(e)}', level='error')
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_requests(request):
    status_filter = request.GET.get('status')  # берём параметр ?status=
    queryset = Request.objects.all().order_by('-id')

    if status_filter:
        queryset = queryset.filter(status__iexact=status_filter.strip())

    data = [
        {
            "request_id": obj.request_id,
            "project": obj.project,
            "device": obj.device,
            "quantity": obj.quantity,
            "date_received": obj.date_received.isoformat(),
            "deadline": obj.deadline.isoformat(),
            "status": obj.status,
        }
        for obj in queryset
    ]
    return JsonResponse(data, safe=False)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_status(request, request_id):
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            status = body.get("status")
            if status not in ["новый", "в работе", "завершён"]:
                return JsonResponse("Некорректный статус")
            req = Request.objects.get(request_id=request_id)
            req.status = status
            req.save()
            return JsonResponse(req.to_dict())

        except Request.DoesNotExist:
            return JsonResponse({"error": "Заявка не найдена"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(["PATCH"])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_list(request):
    data = []
    for r in Request.objects.filter(status='Создан'):
        data.append({
            'request_id': r.request_id,
            'project': r.project,
            'device': r.device,
            'quantity': r.quantity,
            'date_received': r.date_received.strftime('%Y-%m-%d'),
            'deadline': r.deadline.strftime('%Y-%m-%d'),
            'status': r.status,
        })
    return JsonResponse(data, safe=False)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def get_single_request(request, request_id):
    try:
        req = Request.objects.get(request_id=request_id)
        data = {
            "request_id": req.request_id,
            "project": req.project,
            "device": req.device,
            "quantity": req.quantity,
            "date_received": req.date_received.isoformat(),
            "deadline": req.deadline.isoformat(),
            "status": req.status,
        }
        return JsonResponse(data)
    except Request.DoesNotExist:
        return JsonResponse({"error": "Заявка не найдена"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_devices(request, request_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)

        request_id_from_body = data.get("requestId")
        devices = data.get("devices", [])

        if not request_id_from_body or not devices:
            return JsonResponse({'error': 'Некорректные данные'}, status=400)

        # Проверяем, что requestId в URL и в теле совпадают
        if str(request_id_from_body) != str(request_id):
            return JsonResponse({'error': 'Request ID mismatch'}, status=400)

        # Пытаемся найти заявку
        try:
            req = Request.objects.get(request_id=request_id)
        except Request.DoesNotExist:
            return JsonResponse({'error': 'Заявка не найдена'}, status=404)

        # Создаём записи для каждого устройства
        for device in devices:
            atm_serial = device.get("atm")

            ATM.objects.create(
                serial_number=atm_serial,
                accepted_at=timezone.now().date(),  # или date.today() / из body
                model='неизвестна',  # или передавать из тела
                request=req
            )
            log_request_info(logger_app, request, f'Принял банкомат {atm_serial} заявка {request_id}', level='info')
        Request.objects.filter(request_id=request_id).update(status="В работе")
        return JsonResponse({'status': 'ok'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Ошибка разбора JSON'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_device(request):
    atm_number = request.GET.get("code")

    if not atm_number:
        return JsonResponse({"error": "Параметр 'code' обязателен"}, status=400)

    try:
        atm = ATM.objects.get(serial_number=atm_number)
        return JsonResponse({
            "serial_number": atm.serial_number,
            "model": atm.model,
            "accepted_at": atm.accepted_at.isoformat(),
        })
    except ATM.DoesNotExist:
        return JsonResponse({"error": "Устройство не найдено"}, status=404)
