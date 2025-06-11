from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Request, ATM, ATMImage


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'telegram_id', 'is_staff', 'is_active')  # Добавил role
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'telegram_id', 'telegram_code')}),  # Добавил role
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'telegram_id')}),  # Добавил role
    )
admin.site.register(Request)
admin.site.register(ATM)
admin.site.register(ATMImage)