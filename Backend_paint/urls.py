from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Backend_paint_app.urls')),  # подключение всех URL приложения
    path('ping/', lambda request: HttpResponse("Сервер работает!")),  # простой тест
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
