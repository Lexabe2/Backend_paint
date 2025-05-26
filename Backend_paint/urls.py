from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('', lambda request: HttpResponse("Сервер работает!")),
    path('admin/', admin.site.urls),
    path('api/', include('Backend_paint_app.urls')),  # Подключаем API один раз
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)