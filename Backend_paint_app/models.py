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


    def save(self, *args, **kwargs):
        if not self.request_id:
            last = Request.objects.count() + 1
            self.request_id = f'ПОК{last}'
        super().save(*args, **kwargs)
