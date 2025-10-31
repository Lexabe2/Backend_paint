from django.urls import path
from .views import LoginStep1View, VerifyTelegramCodeView, SetTelegramIDView, get_user_profile, \
    server_info, LogView, check_auth, create_request, get_requests, update_status, get_single_request, register_devices, \
    search_device, update_atm, get_atm, complaints, create_reclamation, update_complaint_comment, dashboard, \
    atm_raw_create, warehouse_atms, atm_for_paint, task_paint
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView
from . import views

urlpatterns = [
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/login-step-1/', LoginStep1View.as_view()),
    path('auth/verify-code/', VerifyTelegramCodeView.as_view()),
    path('auth/set-telegram-id/', SetTelegramIDView.as_view()),
    path('check-auth/', check_auth),  # Проверка авторизации
    path('auth/me/', get_user_profile),  # Получение информации о пользователе
    path('server-info/', server_info, name='server_info'),  # Получение информации о сервере
    path('logs/', LogView.as_view(), name='logs'),  # Получение логов
    path('dashboard/', dashboard, name='dashboard'),  # Получение информации для главной станицы
    path('requests/', create_request, name='create-request'),  # Добавление заявки
    path('requests-list/', get_requests, name='request-list'),  # Возвращает заявки
    path("requests/<int:request_id>/", update_status, name="update_status"),  # Изменения статуса заявки
    path("requests-work/<str:request_id>/", get_single_request),  # Приемка
    path('atm-add/<str:request_id>/register-devices/', register_devices),  # Приемка устройства
    path("atm/search/", search_device),  # Поиск банкомата
    path('atm/<int:atm_id>/update/', update_atm, name='update_atm'),  # Добавления комментария к банкомату через поиск
    path('atm-comment/<int:atm_id>/', get_atm, name='get_atm'),  # Просмотр комментариев
    path('complaints/', complaints, name='complaints'),  # Просмотр рекламаций
    path("complaints-add/", create_reclamation),  # Добавление рекламации
    path('complaints/<int:complaint_id>/', update_complaint_comment, name='update_complaint_comment'),
    path("atms/raw_create/", atm_raw_create, name="atm-raw-create"),
    path('atms/warehouse/', warehouse_atms, name='warehouse_atms'),
    path('atm_for_paint/', atm_for_paint, name='atm_for_paint'),
    path('tasks/', task_paint, name='task_paint'),
    path("stages/", views.get_stages, name="get_stages"),
    path("stages/add/", views.add_stage, name="add_stage"),
    path("stages/<int:stage_id>/delete/", views.delete_stage, name="delete_stage"),
    path("stages/<int:stage_id>/works/add/", views.add_work, name="add_work"),
    path("works/<int:work_id>/delete/", views.delete_work, name="delete_work"),
    path("warehouse/", views.warehouse_list, name="warehouse_list"),
    path("warehouse/add/", views.warehouse_add, name="warehouse_add"),
    path("warehouse/<int:pk>/", views.warehouse_update, name="warehouse_update"),
    path("warehouse/<int:pk>/delete/", views.warehouse_delete, name="warehouse_delete"),
    path("atm/<int:atm_id>/photos/", views.atm_photos, name="atm_photos"),
    path("atm/upload-photos/", views.upload_photos, name="upload_photos"),
    path("atm_list/", views.atm_list, name="atm_list"),
    path("otk/", views.otk, name="otk"),
    path("corrections/", views.corrections, name="corrections"),
    path("acceptance_pp/", views.acceptance_pp, name="acceptance_pp"),
    path("status_req/", views.status_req, name="status_req"),
    path("changes_req_atm/", views.changes_req_atm, name="changes_req_atm"),
    path("status_atm/", views.status_atm, name="status_atm"),
    path("atm_act/", views.act, name="act"),
    path('acts/<int:pk>/upload-signature/', views.upload_signature, name='upload_signature'),
]
