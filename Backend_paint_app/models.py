from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('admin_paint', 'Админ_пок'),
        ('admin_pp', 'Админ_пп'),
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
    deadline = models.DateField()
    status = models.TextField(default='Не принят', blank=True, null=True)

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
            "date_received": self.date_received.isoformat(),
            "deadline": self.deadline.isoformat(),
            "status": self.status or ""
        }


class ATM(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    accepted_at = models.DateField()
    model = models.CharField(max_length=100)

    request = models.ForeignKey(
        Request,
        to_field='request_id',
        on_delete=models.CASCADE,
        related_name='atms'
    )

    class Meta:
        verbose_name = "Банкоматы"
        verbose_name_plural = "Банкоматы"

    def __str__(self):
        return f"{self.model} ({self.serial_number})"


class ATMImage(models.Model):
    atm = models.ForeignKey("ATM", related_name="images", on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    photo_type = models.CharField(max_length=100, blank=True, null=False)
    image = models.ImageField(upload_to='atm_photos/')

    class Meta:
        verbose_name = "Фото неисправностей"
        verbose_name_plural = "Фото неисправностей"

    def __str__(self):
        return f"Фото для {self.atm.serial_number}"

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


class ReclamationPhoto(models.Model):
    reclamation = models.ForeignKey(Reclamation, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="reclamations/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Фото для рекламации №{self.reclamation.id}"