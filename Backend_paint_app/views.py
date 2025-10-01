from rest_framework.views import APIView
from django.utils.dateparse import parse_date
from rest_framework.decorators import parser_classes
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, ATM, ATMImage, Reclamation, ReclamationPhoto, ModelAtm, ProjectData, StatusReq, \
    StatusATM, Work, ATMWorkStatus, Stage, WarehouseSlot, WarehouseHistory
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
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models.functions import Substr, Cast
from django.db.models import IntegerField, Max, Sum
from datetime import date
import traceback
from django.db.models import Count
from django.utils import timezone
import base64
from urllib.parse import quote
from PIL import Image
import io

logger = get_logger('user')  # или 'app', 'django' и т.д.
logger_app = get_logger('app')

BOT_TOKEN = os.getenv("BOT_TOKEN")


def role_chat_id(roles):
    if isinstance(roles, str):
        roles = [roles]  # превращаем одиночную строку в список

    chat_ids = CustomUser.objects.filter(role__in=roles) \
        .exclude(telegram_id__isnull=True) \
        .exclude(telegram_id='') \
        .values_list('telegram_id', flat=True)
    return list(chat_ids)


def mess_tel(roles, text):
    for chat_id in role_chat_id(roles):
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                'chat_id': chat_id,
                'text': text,
            }
        )


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
                            'text': f'Код: `{code}`',
                            'parse_mode': 'Markdown'
                        }
                    )
                    #
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    source = request.GET.get("source", "").lower()  # делаем параметр нечувствительным к регистру

    if source == "warehouse":
        # Считаем заявки по статусам
        data_req = list(Request.objects.exclude(status='Закрыта').values("status").annotate(count=Count("id")))
        atm_counts = list(ATM.objects.values('status').annotate(count=Count('id')))
        print(atm_counts)
        return JsonResponse({"data": data_req, 'atm_counts': atm_counts})

    elif source == "paint":
        # Данные для покрасочной
        return JsonResponse({
            "message": "Информация для покрасочной",
            "source": source,
        })

    # По умолчанию пустой объект
    return JsonResponse({"message": "Неизвестный источник"})


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

        required_fields = ['project', 'device', 'quantity']
        if not all(field in data for field in required_fields):
            log_request_info(logger_app, request, 'Не все поля заполнены', level='error')
            return JsonResponse({'error': 'Не все поля заполнены'}, status=400)

        new_request = Request(
            project=data['project'],
            device=data['device'],
            quantity=int(data['quantity']),
            date_received=date.today(),
            deadline=(
                datetime.strptime(data['deadline'], '%Y-%m-%d').date()
                if data.get('deadline')
                else None
            ),
            status=data.get('status') or 'Создана'
        )
        log_request_info(logger_app, request, f'Заявка создана {data}', level='info')
        new_request.save()
        mess_tel('admin',
                 f'Создана заявка {data["project"]} номер {new_request.request_id} кол-во устройств {int(data["quantity"])}')
        req = Request.objects.get(request_id=new_request.request_id)
        StatusReq.objects.create(status='Заявка создана', date_change=date.today(), user=request.user, request=req)

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
    request_id = request.GET.get('id')
    status_filter = request.GET.get('status')  # берём параметр ?status=

    queryset = Request.objects.all().order_by('-id')

    if status_filter:
        queryset = queryset.filter(status__iexact=status_filter.strip())
    elif request_id:
        queryset = queryset.filter(request_id=request_id)

    data = [
        {
            "request_id": obj.request_id,
            "project": obj.project,
            "device": obj.device,
            "quantity": obj.quantity,
            "date_received": obj.date_received.isoformat(),
            "deadline": obj.deadline.isoformat() if obj.deadline else None,
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
            req = Request.objects.get(request_id=request_id)
            req.status = status
            req.save()
            mess_tel('admin',
                     f'Заявка {request_id} принята в работу принял {request.user}')
            req = Request.objects.get(request_id=request_id)
            StatusReq.objects.create(status='Заявка принята покрасочной', date_change=date.today(), user=request.user,
                                     request=req)
            return JsonResponse(req.to_dict())

        except Request.DoesNotExist:
            return JsonResponse({"error": "Заявка не найдена"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(["PATCH"])


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
            "date_received": req.date_received.isoformat() if req.date_received else None,
            "deadline": req.deadline.isoformat() if req.deadline else None,
            "status": req.status
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
            if not ATM.objects.filter(serial_number=atm_serial).exists():
                return JsonResponse({'error': f'Серийный номер {atm_serial} не найден'}, status=404)
            ATM.objects.filter(serial_number=atm_serial).update(status='Принят в покраску')
            atm = ATM.objects.get(serial_number=atm_serial)
            StatusATM.objects.create(status='Принят в покраску', date_change=date.today(), user=request.user, sn=atm)
            log_request_info(logger_app, request, f'Принял банкомат {atm_serial} заявка {request_id}', level='info')
        Request.objects.filter(request_id=request_id).update(status="В покраске")
        req = Request.objects.get(request_id=request_id)
        StatusReq.objects.create(status='В покраске', date_change=date.today(), user=request.user, request=req)
        return JsonResponse({'status': 'ok'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Ошибка разбора JSON'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_device(request):
    atm_number = request.GET.get("code")
    source = request.GET.get("source", "default")
    atm = ATM.objects.get(serial_number=atm_number)

    if not atm_number:
        return JsonResponse({"error": "Параметр 'code' обязателен"}, status=400)

    try:
        if source == "default":
            status_atm = StatusATM.objects.filter(sn=atm)
            status_history = []
            for s in status_atm:
                status_history.append({
                    "status": s.status,
                    "user": s.user.username if s.user else None,
                    "date": s.date_change,
                })
            return JsonResponse({
                "serial_number": atm.serial_number,
                "model": atm.model,
                "accepted_at": atm.accepted_at.isoformat() if atm.accepted_at else None,
                "status": atm.status,
                "status_history": status_history,
            })
        elif source == "paint":
            if not ATM.objects.filter(serial_number=atm_number).exists():
                return JsonResponse({"error": "Устройство не найдено"}, status=404)
            req = ATM.objects.get(serial_number=atm_number).request
            req_data = Request.objects.get(request_id=req.request_id)
            return JsonResponse({
                "serial_number": atm_number,
                "model": atm.model,
                "bank": req_data.project,
            })
    except ATM.DoesNotExist:
        return JsonResponse({"error": "Устройство не найдено"}, status=404)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def update_atm(request, atm_id):
    comment = request.data.get("comment", "").strip()
    model = request.data.get("model", "").strip()
    photo_type = request.data.get("photo_type", "Приемка")  # по умолчанию "Приемка"

    if not atm_id:
        return JsonResponse({"error": "Отсутствует идентификатор банкомата"}, status=400)

    try:
        atm = ATM.objects.get(serial_number=atm_id)
    except ATM.DoesNotExist:
        return JsonResponse({"error": f"Банкомат с номером {atm_id} не найден"}, status=404)

    atm.comment = comment
    atm.photo_type = photo_type
    atm.model = model
    atm.save()
    images = request.FILES.getlist("images")
    if images is not None:
        for img in images:
            ATMImage.objects.create(
                atm=atm,
                comment=comment,
                image=img,
                photo_type=photo_type  # предполагается, что поле есть в ATMImage
            )
    ATMImage.objects.create(atm=atm, comment=comment, photo_type=photo_type)
    log_request_info(logger_app, request, f"Добавил комментарий к {atm_id}", level='info')
    mess_tel('admin', f'Добавлен комментарий к банкомату {atm_id} "{comment}"')

    return JsonResponse({"success": True, "uploaded_images": len(images)}, status=200)


@api_view(["GET"])
def get_atm(request, atm_id):
    try:
        atm = ATM.objects.get(serial_number=atm_id)
    except ATM.DoesNotExist:
        return JsonResponse({"error": "Банкомат не найден"}, status=404)

    data = {
        "serial_number": atm.serial_number,
        "model": atm.model,
        "accepted_at": atm.accepted_at,
        "request_id": atm.request.request_id,
        "images": []
    }

    for image in atm.images.all():
        image_data = {
            "id": image.id,
            "image": request.build_absolute_uri(image.image.url) if image.image else None,
            "comment": image.comment,
            "photo_type": image.photo_type,
        }
        data["images"].append(image_data)

    return JsonResponse(data, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def complaints(request):
    reclamations = Reclamation.objects.prefetch_related("photos").all()

    result = []
    for rec in reclamations:
        result.append({
            "id": rec.id,
            "serial_number": rec.serial_number,
            "due_date": rec.due_date,
            "created_at": rec.created_at,
            "status": rec.get_status_display(),
            "remarks": rec.remarks,
            "comment_remarks": rec.comment_remarks,
            "remarks_corrections": rec.remarks_corrections,
            "is_overdue": rec.is_overdue if rec.status in ["pending", "in_progress", "in_check"] else False,
            "photos": [request.build_absolute_uri(photo.image.url) for photo in rec.photos.all()]
        })

    return JsonResponse(result, safe=False)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_reclamation(request):
    serial_number = request.POST.get("serial_number")
    due_date = request.POST.get("due_date")
    remarks = request.POST.get("remarks")

    if not serial_number:
        return Response({"error": "Серийный номер обязателен"}, status=400)

    # Создаём рекламацию
    reclamation = Reclamation.objects.create(
        serial_number=serial_number,
        due_date=due_date,
        remarks=remarks,
        created_by=request.user
    )

    # Обрабатываем все переданные фотографии
    for file in request.FILES.getlist("photos"):
        ReclamationPhoto.objects.create(
            reclamation=reclamation,
            image=file
        )
    mess_tel(['admin', 'admin_paint'], f'Создана рекламация к банкомату {serial_number} замечания {remarks}')
    return Response({
        "message": "Рекламация успешно создана",
        "id": reclamation.id,
        "serial_number": reclamation.serial_number,
        "photos": [photo.image.url for photo in reclamation.photos.all()]
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_complaint_comment(request, complaint_id):
    try:
        body = request.data  # DRF сам разберёт JSON

        complaint = Reclamation.objects.get(id=complaint_id)

        # Обновление полей, если переданы
        if "comment_remarks" in body:
            comment = body["comment_remarks"]
            complaint.comment_remarks = comment
            complaint.status = 'in_progress'
            complaint.save()
            mess_tel(
                ['admin', 'admin_pp'],
                f'Взят в работу банкомат {complaint.serial_number} комментарий: {comment}'
            )
            return JsonResponse({"status": "success", "message": "Комментарий сохранён"})

        elif "comment_good" in body:
            comment = body["comment_good"]
            complaint.remarks_corrections = comment  # убедись, что такое поле есть в модели!
            complaint.status = 'in_check'
            complaint.save()
            mess_tel(
                ['admin', 'admin_paint'],
                f'Рекламация ожидает проверки {complaint.serial_number} комментарий: {comment}'
            )
            return JsonResponse({"status": "success", "message": "Рекламация закрыта"})


        elif body.get("rejected") is True:
            complaint.status = 'pending'
            complaint.save()
            mess_tel(['admin', 'admin_pp'], f'Рекламация отклонена: {complaint.serial_number}')
            return JsonResponse({"status": "success", "message": "Отклонено"})

        elif body.get("approved") is True:
            complaint.status = 'resolved'
            complaint.save()
            mess_tel(['admin', 'admin_pp'], f'Рекламация принята: {complaint.serial_number}')
            return JsonResponse({"status": "success", "message": "Отклонено"})

        else:
            return JsonResponse({"status": "error", "message": "Комментарий не передан"}, status=400)

    except Reclamation.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Рекламация не найдена"}, status=404)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_photos(request):
    sn = request.POST.get("sn")
    status = request.POST.get("status")
    comment = request.POST.get("comment", "")
    files = request.FILES.getlist("photos")
    defect = request.POST.get("defect")
    atm = ATM.objects.get(serial_number=sn)

    if not sn:
        return JsonResponse({"error": "Не передан SN"}, status=400)

    saved_files = []
    save_dir = os.path.join(settings.MEDIA_ROOT, "atm_photos")
    os.makedirs(save_dir, exist_ok=True)

    for idx, f in enumerate(files):
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            ext = ".jpg"  # конвертируем всё в jpg
        if status == "Без статуса":
            save_name = f"{sn}_{defect}_{idx}{ext}"
        else:
            save_name = f"{sn}_{status}_{idx}{ext}"
        save_path = os.path.join(save_dir, save_name)

        # Читаем файл в Pillow
        img = Image.open(f)

        # Ограничим размер (например, до 1600px по ширине/высоте)
        max_size = (1920, 1600)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Сохраняем с сжатием
        img.save(save_path, format="JPEG", quality=85, optimize=True)

        saved_files.append(save_name)

    # Запись в БД
    ATMImage.objects.create(
        atm=atm,
        comment=comment,
        photo_type=status,
        images_data=saved_files
    )

    return JsonResponse({
        "message": "Файлы успешно сохранены",
        "files": saved_files
    })


def dec_photo(sn, photos_data, comment, stage):
    atm = ATM.objects.get(serial_number=sn)
    saved_files = []

    for idx, photo in enumerate(photos_data):
        photo_str = photo.get("data", "")
        if not photo_str:
            continue

        if ";base64," in photo_str:
            _, imgstr = photo_str.split(";base64,")
        else:
            imgstr = photo_str

        image_bytes = base64.b64decode(imgstr)
        filename = f"{sn}_{stage}_{idx}.jpg"

        folder_path = "media/atm_photos/"
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)

        # Загружаем изображение в Pillow
        img = Image.open(io.BytesIO(image_bytes))

        # Опционально: уменьшаем разрешение (например, ширина макс. 1600px)
        max_size = (1600, 1600)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Сохраняем сжатое фото
        img.save(file_path, format="JPEG", quality=85, optimize=True)

        # Проверка
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            saved_files.append(f"atm_photos/{filename}")
        else:
            return False

    if saved_files:
        ATMImage.objects.create(
            atm=atm,
            comment=comment,
            photo_type=stage,
            images_data=saved_files
        )
        return True

    return False


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def atm_photos(request, atm_id):
    try:
        atm = ATM.objects.get(serial_number=atm_id)
    except ATM.DoesNotExist:
        return JsonResponse({"error": "ATM not found"}, status=404)

    images = ATMImage.objects.filter(atm=atm)
    grouped_photos = {}
    env = os.getenv("DJANGO_ENV", "development")  # default developmen
    for img in images:
        for path in img.images_data or []:
            url_path = quote(path, safe="/")
            if env == "development":
                full_url = request.build_absolute_uri(settings.MEDIA_URL + 'atm_photos/' + url_path)
            else:
                full_url = request.build_absolute_uri(settings.MEDIA_URL + url_path)

            # Извлекаем статус
            filename = path.split("/")[-1]
            parts = filename.split("_")
            status = "_".join(parts[1:-1]) if len(parts) > 2 else "Неизвестно"

            if status not in grouped_photos:
                grouped_photos[status] = []

            grouped_photos[status].append(full_url)
    return JsonResponse({"photos": grouped_photos})


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def atm_raw_create(request):
    if request.method == "GET":
        try:
            last_num = (
                           ATM.objects
                           .filter(pallet__startswith="PP")
                           .annotate(pallet_num=Cast(Substr("pallet", 3), IntegerField()))
                           .aggregate(max_num=Max("pallet_num"))
                       )["max_num"] or 0  # если None, то ставим 0

            models = ModelAtm.objects.all()
            model_list = [m.model for m in models]

            return JsonResponse(
                {"pallet": last_num + 1, "model": model_list},
                status=200,
                json_dumps_params={"ensure_ascii": False},
            )

        except Exception as e:
            error_text = f"Ошибка в atm_raw_create: {e}"
            logger.error(error_text)
            logger_app.error(error_text)
            traceback_str = traceback.format_exc()
            logger.error(traceback_str)
            logger_app.error(traceback_str)

            return JsonResponse({"error": str(e)}, status=500)
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        reception = data.get("reception")
        status = None
        if reception == 'new':
            status = 'Принят на склад'
        elif reception == 'paint':
            status = 'Принят из покраски "Другая"'
        serial = data.get("serial_number")
        model = data.get("model")
        accepted_at = data.get("accepted_at")
        pallet = data.get("pallet")
        user = request.user
        photos_data = request.data.get("photos", [])  # массив base64
        comment = request.data.get("comment", "")
        errors = {}
        if not serial:
            errors["serial_number"] = "Обязательное поле."
        if not model:
            errors["model"] = "Обязательное поле."
        if not accepted_at:
            errors["accepted_at"] = "Обязательное поле."
        else:
            parsed = parse_date(accepted_at)
            if parsed is None:
                errors["accepted_at"] = "Неверный формат даты (ожидается YYYY-MM-DD)."
        if not pallet:
            errors["pallet"] = "Обязательное поле."

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        if ATM.objects.filter(serial_number=serial).exists():
            return JsonResponse({"detail": "ATM с таким серийным номером уже существует."}, status=400)

        # обработка request_id
        request_obj = None
        request_id = data.get("request_id")
        if request_id:
            try:
                request_obj = Request.objects.get(request_id=request_id)
            except Request.DoesNotExist:
                return JsonResponse({"detail": "Указанный request_id не найден."}, status=400)

        ATM.objects.create(
            serial_number=serial,
            model=model,
            pallet=f"PP{pallet}",
            accepted_at=parse_date(accepted_at),
            request=request_obj,
            status=status,
            user=user
        )

        photos_saved = None
        if photos_data:  # только если список не пустой
            photos_saved = dec_photo(serial, photos_data, comment, status)

        atm = ATM.objects.get(serial_number=serial)
        StatusATM.objects.create(
            status='Принят на склад',
            date_change=date.today(),
            user=request.user,
            sn=atm
        )

        resp = {
            "id": atm.id,
            "serial_number": atm.serial_number,
            "model": atm.model,
            "accepted_at": atm.accepted_at.isoformat(),
            "pallet": atm.pallet,
            "photos_saved": photos_saved  # null если не было фото, true/false — если были
        }
        return JsonResponse(resp, status=201)
    return None


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def warehouse_atms(request):
    # Банкоматы со статусом "Принят на склад"
    atms = ATM.objects.filter(status="Принят на склад")
    reserve = (
                  Request.objects
                  .filter(status="На согласование(покрасочная)")
                  .aggregate(total=Sum("quantity"))
              )["total"] or 0

    # Последняя заявка
    last_request = Request.objects.order_by('-request_id').first()
    last_request_data = last_request.request_id if last_request else 0

    # Проекты
    project_data_list = [
        {
            'project': i.project,
            'deadlines': i.deadlines,
            'comments': i.comments
        }
        for i in ProjectData.objects.all()
    ]

    # Банкоматы
    atms_data = [
        {
            "id": atm.id,
            "serial_number": atm.serial_number,
            "model": atm.model,
            "pallet": atm.pallet,
            "status": atm.status,
        }
        for atm in atms
    ]

    return JsonResponse({
        "count": atms.count() - reserve,
        "atms": atms_data,
        "project_data": project_data_list,
        "last_request": int(last_request_data) + 1,
    })


@api_view(["POST", "GET", "DELETE"])
@permission_classes([IsAuthenticated])
def atm_for_paint(request):
    if request.method == "GET":
        request_id = request.GET.get("request_id")
        atms = ATM.objects.filter(request_id=request_id)
        # Преобразуем QuerySet в список словарей
        data = [
            {
                "id": atm.id,
                "model": atm.model,
                "serial_number": atm.serial_number,
                "pallet": atm.pallet,
            }
            for atm in atms
        ]
        return JsonResponse({"atms": data}, safe=False, json_dumps_params={'ensure_ascii': False})

    if request.method == "POST":
        sn = request.data.get("sn")
        request_id = request.data.get("request_id")
        if not sn or not request_id:
            return JsonResponse({"error": "Не передан sn или request_id"}, status=400)
        try:
            atm = ATM.objects.get(serial_number=sn)
        except ATM.DoesNotExist:
            return JsonResponse({"error": f"Банкомат с SN {sn} не найден"}, status=404)
        try:
            req = Request.objects.get(request_id=request_id)
        except Request.DoesNotExist:
            return JsonResponse({"error": f"Заявка с id {request_id} не найдена"}, status=404)
        atm.request = req
        atm.status = 'Готов к передаче в покраску'
        atm.save()
        atm = ATM.objects.get(serial_number=sn)
        StatusATM.objects.create(status='Готов к передаче в покраску', date_change=date.today(), user=request.user,
                                 sn=atm)
        count_atm_req = Request.objects.get(request_id=request_id).quantity
        count_atm = ATM.objects.filter(request=request_id).count()
        if count_atm == count_atm_req:
            Request.objects.filter(request_id=request_id).update(status="Готова к передачи в покраску")
            StatusReq.objects.create(status='Заявка готова к передаче в покраску', date_change=date.today(),
                                     user=request.user, request=req)
            mess_tel(['admin', 'admin_paint'],
                     f'Заявка {request_id} готова к передачи в покраску')
        return JsonResponse({"message": "POST успешно"}, status=201)
    if request.method == "DELETE":
        request_id = request.data.get("request_id")
        serial_number = request.data.get("serial_number")
        count_atm_req = Request.objects.get(request_id=request_id).quantity
        count_atm = ATM.objects.filter(request=request_id).count()
        if count_atm == count_atm_req:
            StatusReq.objects.create(status='Заявка возвращена в статус "Заявка принята(покрасочная)"',
                                     date_change=date.today(), user=request.user, request=request_id)
            Request.objects.filter(request_id=request_id).update(status="Заявка принята(покрасочная)")
        if not serial_number:
            return JsonResponse({"error": "Не передан atm_id"}, status=400)
        try:
            atm = ATM.objects.get(serial_number=serial_number)
        except ATM.DoesNotExist:
            return JsonResponse({"error": f"Банкомат с id {serial_number} не найден"}, status=404)

        # Отвязать банкомат от заявки
        atm.request = None
        atm.save()

        return JsonResponse({"message": "Банкомат удалён из заявки"}, status=200)
    return None


def assign_works_to_atm(atm: ATM):
    all_works = Work.objects.all()
    for work in all_works:
        ATMWorkStatus.objects.create(
            atm=atm,
            work=work,
            completed=False,
            completed_at=None,
            employee=None
        )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_paint(request):
    if request.method == "GET":
        sn = request.GET.get("sn")
        source = request.GET.get("source", "default")
        if not sn:
            return JsonResponse({"error": "Не передан серийный номер"}, status=400)

        try:
            atm = ATM.objects.get(serial_number=sn)
        except ATM.DoesNotExist:
            return JsonResponse({"error": "Устройство не найдено"}, status=404)

        # фильтруем по этапу
        if source == "paint":
            statuses = atm.work_statuses.filter(work__stage__name="Покраска").select_related("work", "employee")
        else:
            statuses = atm.work_statuses.all().select_related("work", "employee")

        data = []
        for s in statuses:
            if not s.work:
                continue

            # словарь сотрудник → True/False
            all_statuses = {
                str(ws.employee.id): ws.completed
                for ws in ATMWorkStatus.objects.filter(atm=atm, work=s.work).exclude(employee__isnull=True)
            }

            completed = all(all_statuses.values()) if all_statuses else False

            data.append({
                "id": s.work.id,
                "name": s.work.name,
                "statuses": all_statuses,
                "completed": completed,
            })
        return JsonResponse(data, safe=False)
    if request.method == "POST":
        atm_sn = request.data.get("sn")
        task_names = request.data.get("tasks", [])
        atm = ATM.objects.get(serial_number=atm_sn)
        for task_name in task_names:
            try:
                Work.objects.get(name=task_name)
            except Work.DoesNotExist:
                continue
            ATMWorkStatus.objects.filter(
                atm=atm,
                work__name__in=task_names
            ).update(
                completed=True,
                completed_at=timezone.now(),
                employee=request.user
            )
            source = request.GET.get("source", "default")
            if source == "paint":
                all_completed = not ATMWorkStatus.objects.filter(
                    atm=atm,
                    work__stage__name="Покраска",
                    completed=False
                ).exists()
                if all_completed:
                    ATM.objects.filter(serial_number=atm_sn).update(status='Готов к передаче в ПП')
        return JsonResponse({'error': 'aas'})
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_stages(request):
    stages = Stage.objects.all().prefetch_related("works")
    data = []
    for stage in stages:
        data.append({
            "id": stage.id,
            "name": stage.name,
            "works": [{"id": w.id, "name": w.name} for w in stage.works.all()]
        })
    return JsonResponse(data, safe=False)


# Добавление нового этапа
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_stage(request):
    try:
        name = request.data.get("name")
        if not name:
            return JsonResponse({"error": "Не указано имя этапа"}, status=400)
        stage = Stage.objects.create(name=name)
        return JsonResponse({"id": stage.id, "name": stage.name})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Удаление этапа
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_stage(request, stage_id):
    try:
        stage = Stage.objects.get(id=stage_id)
        stage.delete()
        return JsonResponse({"success": True})
    except Stage.DoesNotExist:
        return JsonResponse({"error": "Этап не найден"}, status=404)


# Добавление работы к этапу
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_work(request, stage_id):
    try:
        stage = Stage.objects.get(id=stage_id)
        name = request.data.get("name")
        if not name:
            return JsonResponse({"error": "Не указано имя работы"}, status=400)
        work = Work.objects.create(stage=stage, name=name)
        return JsonResponse({"id": work.id, "name": work.name, "stage": stage.name})
    except Stage.DoesNotExist:
        return JsonResponse({"error": "Этап не найден"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Удаление работы
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_work(request, work_id):
    try:
        work = Work.objects.get(id=work_id)
        work.delete()
        return JsonResponse({"success": True})
    except Work.DoesNotExist:
        return JsonResponse({"error": "Работа не найдена"}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def warehouse_list(request):
    """Список всех мест с историей изменений"""
    slots_data = []

    slots = WarehouseSlot.objects.all().order_by("place_number")
    for slot in slots:
        # Берем историю для этого места, сортируем по дате
        history = WarehouseHistory.objects.filter(place_number=slot.place_number).order_by("-date_added")
        history_list = [
            {
                "id": h.id,
                "description": h.description,
                "action": h.get_action_display(),
                "date_added": h.date_added,
                "user": h.user.username if h.user else None,
            }
            for h in history
        ]

        slots_data.append({
            "id": slot.id,
            "place_number": slot.place_number,
            "description": slot.description,
            "date_added": slot.date_added,
            "history": history_list
        })

    return JsonResponse({"slots": slots_data}, safe=False, json_dumps_params={"ensure_ascii": False})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def warehouse_add(request):
    """Добавить запись"""
    data = json.loads(request.body)
    place_number = data.get("place_number")

    # Проверяем, существует ли уже такое место
    if WarehouseSlot.objects.filter(place_number=place_number).exists():
        return JsonResponse(
            {"error": f"Место {place_number} уже занято"},
            status=400
        )

    # Создаём новую запись
    slot = WarehouseSlot.objects.create(
        place_number=place_number,
        description=data.get("description", "")
    )

    return JsonResponse({
        "id": slot.id,
        "place_number": slot.place_number,
        "description": slot.description,
        "date_added": slot.date_added
    }, json_dumps_params={"ensure_ascii": False})


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def warehouse_update(request, pk):
    """Изменить запись"""
    if request.method in ["PUT", "PATCH"]:
        try:
            slot = WarehouseSlot.objects.get(pk=pk)
        except WarehouseSlot.DoesNotExist:
            return JsonResponse({"error": "Запись не найдена"}, status=404)
        data = json.loads(request.body)
        if "place_number" in data and data["place_number"] != slot.place_number:
            WarehouseHistory.objects.create(
                place_number=data["place_number"],
                description=f'Изменил место: было {slot.place_number}, стало {data["place_number"]}',
                action="update",
                date_added=datetime.now(),
                user=request.user,
            )
            slot.place_number = data["place_number"]

        # Проверяем, изменилось ли описание
        if "description" in data and data["description"] != slot.description:
            WarehouseHistory.objects.create(
                place_number=data.get("place_number", slot.place_number),
                description=f'Изменил описание: было "{slot.description}", стало "{data["description"]}"',
                action="update",
                date_added=datetime.now(),
                user=request.user,
            )
            slot.description = data["description"]

        slot.save()

        return JsonResponse({
            "id": slot.id,
            "place_number": slot.place_number,
            "description": slot.description,
            "date_added": slot.date_added
        }, json_dumps_params={"ensure_ascii": False})
    return None


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def warehouse_delete(request, pk):
    """Удалить запись"""
    if request.method == "DELETE":
        try:
            slot = WarehouseSlot.objects.get(pk=pk)
        except WarehouseSlot.DoesNotExist:
            return JsonResponse({"error": "Запись не найдена"}, status=404)
        WarehouseHistory.objects.create(
            place_number=slot.place_number,
            description='Удалено',
            action="delete",
            date_added=datetime.now(),
            user=request.user,
        )
        slot.delete()
        return JsonResponse({"success": True})
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def atm_list(request):
    page = request.GET.get("page")
    if page == 'otk':
        atms = ATM.objects.filter(status__in=['Исправлен', 'Окрашен', 'Принят из покраски "Другая"']).values(
            "serial_number", "pallet",
            "model")
        return JsonResponse({"atms": list(atms)})
    elif page == 'corrections':
        atms = ATM.objects.filter(status='Возврат в покрасочную').values(
            "serial_number", "pallet",
            "model")
        return JsonResponse({"atms": list(atms)})
    elif page == 'viewing':
        atms = ATM.objects.all().values(
            "serial_number", "pallet", 'status' ,
            "model", "accepted_at")
        return JsonResponse({"atms": list(atms)})
    return None


def add_status_atm(sn, status, request):
    atm = ATM.objects.get(serial_number=sn)
    ATM.objects.filter(serial_number=sn).update(status=status)
    StatusATM.objects.create(sn=atm, status=status, date_change=datetime.now(), user=request.user)
    return True


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def otk(request):
    if request.method == "GET":
        query = request.GET.get("query")  # получаем параметр query
        if not query:
            return JsonResponse({"error": "Не указан query"}, status=400)

        atms = ATM.objects.filter(serial_number=query) | ATM.objects.filter(pallet=query)
        atms = atms.values("serial_number", "pallet", "model", "status", "accepted_at")

        return JsonResponse({"atms": list(atms)})
    elif request.method == "POST":
        data = json.loads(request.body)
        sn = data.get("atmSerial")
        has_issues = data.get("hasIssues")
        if has_issues:
            status = 'Возврат в покрасочную'
            mess_tel(['admin', 'admin_paint'], f'Банкомат {sn} возвращен, не прошел ОТК')
        else:
            status = 'Готов к передаче в ПП'
        add_status_atm(sn, status, request)
        return JsonResponse({"status": has_issues})
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def corrections(request):
    if request.method == "POST":
        sn = request.data.get("atmSerial")  # <-- вместо GET
        add_status_atm(sn, 'Исправлен', request)
        mess_tel(['admin', 'storekeeper'], f'Банкомат {sn} исправлен')
        return JsonResponse({"status": True})
    return None
