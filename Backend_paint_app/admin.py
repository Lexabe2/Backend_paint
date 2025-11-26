from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Request, ATM, ATMImage, ReclamationPhoto, Reclamation, ModelAtm, ProjectData, StatusReq, \
    StatusATM, Work, Stage, ATMWorkStatus, WarehouseSlot, WarehouseHistory, InvoicePaint, Flow, SerialNumber


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
admin.site.register(ATMImage)
admin.site.register(ModelAtm)
admin.site.register(ProjectData)
admin.site.register(StatusReq)
admin.site.register(StatusATM)
admin.site.register(Work)
admin.site.register(Stage)
admin.site.register(ATMWorkStatus)
admin.site.register(WarehouseSlot)
admin.site.register(WarehouseHistory)
admin.site.register(InvoicePaint)
admin.site.register(Flow)
admin.site.register(SerialNumber)


@admin.register(ATM)
class ATMAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'model', 'pallet', 'status', 'user', 'request', 'score_paint')

    # 🔹 Фильтр по заявке
    list_filter = ('request', 'status', 'score_paint')  # добавь другие поля, если нужно

    # 🔹 Поиск по серийному номеру
    search_fields = ('serial_number', 'model')  # можно добавить model для поиска по модели


class ReclamationPhotoInline(admin.TabularInline):
    model = ReclamationPhoto
    extra = 1


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ('id', 'serial_number', 'created_at')
    inlines = [ReclamationPhotoInline]
