from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('admin_paint', 'Админ_пок'),
        ('storekeeper', 'Кладовщик'),
        ('moderator', 'Модератор'),
        ('user', 'Пользователь'),
    ]

    role = models.CharField(
        max_length=15,
        choices=ROLE_CHOICES,
        default='user',
    )
    telegram_id = models.CharField(max_length=64, blank=True, null=True)
    telegram_code = models.CharField(max_length=6, blank=True, null=True)

    def generate_telegram_code(self):
        code = str(random.randint(100000, 999999))
        self.telegram_code = code
        self.save()
        return code


class Request(models.Model):
    request_id = models.CharField(max_length=10, unique=True, blank=True)
    project = models.CharField(max_length=100)
    device = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    date_received = models.DateField()
    deadline = models.DateField(null=True, blank=True)
    status = models.TextField(default='Создана', blank=True, null=True)

    class Meta:
        verbose_name = "Заявки"
        verbose_name_plural = "Заявки"

    def save(self, *args, **kwargs):
        if not self.request_id:
            last = Request.objects.count() + 1
            self.request_id = last
        super().save(*args, **kwargs)

    def __str__(self):
        return self.request_id

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "project": self.project,
            "device": self.device,
            "quantity": self.quantity,
            "date_received": self.date_received.isoformat() if self.date_received else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
        }


class ATM(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    accepted_at = models.DateField()
    model = models.CharField(max_length=100)
    pallet = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    request = models.ForeignKey(
        Request,
        to_field='request_id',
        on_delete=models.CASCADE,
        related_name='atms',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Банкомат"
        verbose_name_plural = "Банкоматы"

    def save(self, *args, **kwargs):
        if self.pallet and not self.pallet.startswith("PP"):
            self.pallet = f"PP{self.pallet}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.serial_number} {self.model} {self.status} {self.pallet} {self.user}"


class ModelAtm(models.Model):
    model = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Модель"
        verbose_name_plural = "Модели"


class ATMImage(models.Model):
    atm = models.ForeignKey("ATM", related_name="images", on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    photo_type = models.CharField(max_length=100, blank=True)
    images_data = models.JSONField(null=True, blank=True)  # список фото в base64

    class Meta:
        verbose_name = "Фото"
        verbose_name_plural = "Фото"


from django.contrib.auth import get_user_model

User = get_user_model()


class Reclamation(models.Model):
    STATUS_CHOICES = [
        ("pending", "В ожидании"),
        ("in_progress", "В работе"),
        ("in_check", "На проверке"),
        ("resolved", "Исправлено"),
        ("rejected", "Отклонено"),
    ]

    serial_number = models.CharField(
        max_length=100,
        verbose_name="Серийный номер"
    )

    due_date = models.DateField(
        verbose_name="Срок выполнения",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        blank=True,
        null=True,
        verbose_name="Статус"
    )

    remarks = models.TextField(
        null=True,
        blank=True,
        verbose_name="Комментарий рекламации"
    )

    comment_remarks = models.TextField(
        null=True,
        blank=True,
        verbose_name="Комментарий к рекламации"
    )

    remarks_corrections = models.TextField(
        null=True,
        blank=True,
        verbose_name="Комментарий исправления"
    )

    created_by = models.ForeignKey(
        User,
        related_name="created_reclamations",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Создатель"
    )

    updated_by = models.ForeignKey(
        User,
        related_name="processed_reclamations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Обработал"
    )

    class Meta:
        verbose_name = "Рекламация"
        verbose_name_plural = "Рекламации"
        ordering = ['-created_at']

    def __str__(self):
        return f"Рекламация №{self.id} — {self.serial_number}"

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < timezone.now().date()

    def to_dict(self):
        return {
            "id": self.id,
            "serialNumber": self.serial_number,
            "dueDate": self.due_date.isoformat() if self.due_date else None,
            "createdAt": self.created_at.isoformat(),
            "status": self.get_status_display(),  # "В ожидании"
            "remarks": self.remarks,
            "commentRemarks": self.comment_remarks,
            "remarksCorrections": self.remarks_corrections,
            "createdBy": self.created_by.username if self.created_by else None,
            "updatedBy": self.updated_by.username if self.updated_by else None,
            "isOverdue": self.is_overdue,
        }


class ReclamationPhoto(models.Model):
    reclamation = models.ForeignKey(Reclamation, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="reclamations/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Фото для рекламации №{self.reclamation.id}"


class ProjectData(models.Model):
    project = models.CharField(max_length=10, null=False, unique=True)
    deadlines = models.IntegerField(null=False, blank=True)
    comments = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Данные по проекту"
        verbose_name_plural = "Данные по проектам"

    def __str__(self):
        return f'{self.project} {self.deadlines} {str(self.comments)}'


class StatusReq(models.Model):
    status = models.CharField(max_length=30, null=False, unique=True)
    date_change = models.DateField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    request = models.ForeignKey(
        Request,
        to_field='request_id',
        on_delete=models.CASCADE,
        related_name='status_requests',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Изменение статусов заявки"
        verbose_name_plural = "Изменение статусов заявок"


class StatusATM(models.Model):
    status = models.CharField(max_length=50, null=False)
    date_change = models.DateField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    sn = models.ForeignKey(
        ATM,
        to_field='serial_number',
        on_delete=models.CASCADE,
        related_name='status_ATM',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Изменение статусов банкомата"
        verbose_name_plural = "Изменение статусов банкоматов"


class Stage(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Этап банкомата"
        verbose_name_plural = "Этапы банкоматов"


class Work(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="works")
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.stage.name} → {self.name}"

    class Meta:
        verbose_name = "Список работ по банкомату"
        verbose_name_plural = "Список работ по банкоматам"


class ATMWorkStatus(models.Model):
    atm = models.ForeignKey("ATM", on_delete=models.CASCADE, related_name="work_statuses")
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="statuses")
    employee = models.ForeignKey("CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("atm", "work")  # одна работа для одного банкомата не дублируется
        verbose_name = "Работа по банкомату"
        verbose_name_plural = "Работы по банкоматам"

    def __str__(self):
        return f"{self.atm.serial_number} → {self.work.name} ({'OK' if self.completed else 'в процессе'})"
