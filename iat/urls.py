# iat/urls.py

from django.contrib import admin
from django.urls import path, include # Добавьте include # Это уже есть
from django.conf import settings
from django.conf.urls.static import static
from st import views as st_views # Импортируйте ваши views

# ЗДЕСЬ НУЖЕН ИМПОРТ views ИЗ ПРИЛОЖЕНИЯ st, ЕСЛИ ВЫ ХОТИТЕ ИСПОЛЬЗОВАТЬ views ПРЯМО ЗДЕСЬ
# Например: from st import views (или from st.views import ...)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('store/', include('st.urls')), # Это правильный способ подключения URL из приложения st
    path('', st_views.TechTypeListView.as_view(), name='home'), # Пример: главная - список типов техники
 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)