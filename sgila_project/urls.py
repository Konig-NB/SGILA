"""
SGILA Main URL Configuration
/api/...  → All API endpoints (used by the JS frontend)
/admin/   → Django admin panel (for managing content)
/         → Frontend HTML pages (for the web interface)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', include('lessons.urls')),  # Frontend HTML pages
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
