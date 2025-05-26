from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('Backend_paint_app.urls')),  # Подключаем API
    path('', lambda request: HttpResponse("Сервер работает!")),  # Заглушка для корня — последней
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)