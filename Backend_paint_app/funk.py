from .models import ATM, Request, StatusReq, StatusATM
from datetime import date
from django.core.exceptions import ObjectDoesNotExist


def changes_req(req, status, request):
    Request.objects.filter(request_id=req).update(status=status)
    ATM.objects.filter(request=Request.objects.get(request_id=req)).update(status=status)
    StatusReq.objects.create(status=status, date_change=date.today(), user=request.user,
                             request=Request.objects.get(request_id=req))
    atms = ATM.objects.filter(request=Request.objects.get(request_id=req))
    for atm in atms:
        StatusATM.objects.create(status=f'Изменен на статус {status} (заявки)', date_change=date.today(), user=atm.user,
                                 sn=ATM.objects.get(serial_number=atm.serial_number))
    return True


def changes_req_atm_funk(req_id, sn, request):
    atm = ATM.objects.get(serial_number=sn)
    req = Request.objects.get(request_id=req_id)

    StatusATM.objects.create(
        status=f'Добавлен к заявке {req_id}',
        date_change=date.today(),
        user=request.user,
        sn=atm
    )

    ATM.objects.filter(serial_number=sn).update(
        request=req,
        status=req.status
    )

    return True


from datetime import date
from django.core.exceptions import ObjectDoesNotExist
from .models import ATM, StatusATM


def changes_status_atm_funk(sn, new_status, request):
    try:
        # Получаем банкомат
        atm = ATM.objects.get(serial_number=sn)
        # Обновляем статус
        atm.status = new_status
        atm.save()

        # Создаём запись в истории
        StatusATM.objects.create(
            status=f'Изменен на статус {new_status} (ручное изменение)',
            date_change=date.today(),
            user=request.user,
            sn=atm
        )

        return {"success": True, "message": "Статус успешно изменён"}

    except ObjectDoesNotExist:
        return {"success": False, "message": f"Банкомат с серийным номером {sn} не найден"}

    except Exception as e:
        return {"success": False, "message": f"Ошибка при изменении статуса: {str(e)}"}
