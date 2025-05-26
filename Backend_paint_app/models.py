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
