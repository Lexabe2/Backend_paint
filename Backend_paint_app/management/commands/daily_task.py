from django.core.management.base import BaseCommand
from Backend_paint_app.models import Reclamation
from Backend_paint_app.views import mess_tel
from django.utils.timezone import now

class Command(BaseCommand):
    help = 'Ежедневная задача'
    def handle(self, *args, **kwargs):
        reclamations = Reclamation.objects.filter(status__in=['in_progress', 'pending'])

        for rec in reclamations:
            if not rec.is_overdue:
                mess_tel(['admin', 'admin_paint'], f'Рекламация к банкомату просрочена {rec.serial_number}')
        print(f"Задача запущена: {now()}")
        # Пример:
