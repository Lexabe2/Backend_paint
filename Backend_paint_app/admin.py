from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Request, ATM, ATMImage, ModelAtm, ProjectData, StatusReq, \
    StatusATM, Work, Stage, ATMWorkStatus, WarehouseSlot, WarehouseHistory, InvoicePaint

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


@admin.register(ATM)
class ATMAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'model', 'pallet', 'status', 'user', 'request', 'score_paint')

    list_filter = ('request', 'status', 'score_paint')

    search_fields = ('serial_number', 'model')

    actions = ['add_to_invoice', 'remove_from_invoice']

    # Добавить в счет
    @admin.action(description="Добавить в счет")
    def add_to_invoice(self, request, queryset):
        queryset.update(score_paint="Не добавлен в счет")

    # Убрать из счета
    @admin.action(description="Убрать из счета")
    def remove_from_invoice(self, request, queryset):
        queryset.update(score_paint="Без акта")