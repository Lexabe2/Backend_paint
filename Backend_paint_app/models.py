from django.contrib.auth.models import AbstractUser
from django.db import models
import random


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('moderator', 'Модератор'),
        ('user', 'Пользователь'),
    ]

    role = models.CharField(
        max_length=10,
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

    def __str__(self):
        return f"{self.model} ({self.serial_number})"


class ATMImage(models.Model):
    atm = models.ForeignKey("ATM", related_name="images", on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    photo_type = models.CharField(max_length=100, blank=True, null=False)
    image = models.ImageField(upload_to='atm_photos/')

    def __str__(self):
        return f"Фото для {self.atm.serial_number}"
