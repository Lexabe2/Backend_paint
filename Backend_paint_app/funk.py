from .models import ATM, Request, StatusReq, StatusATM
from datetime import date


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


def changes_req_atm_funk(req, sn, request):
    StatusATM.objects.create(status=f'Добавлен к заявке {req}', date_change=date.today(), user=request.user,
                             sn=ATM.objects.get(serial_number=sn))
    ATM.objects.filter(serial_number=Request.objects.get(request_id=sn)).update(
        request=Request.objects.get(request_id=req), status=Request.objects.get(request_id=req).status)
    return True
