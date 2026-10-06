"""
SGILA Main URL Configuration
/api/...  → All API endpoints (used by the JS frontend)
/admin/   → Django admin panel (for managing content)
/         → Frontend HTML pages (for the web interface)
"""
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


handler404 = 'sgila_project.urls.custom_404'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('schools.urls')),  # /api/schools/search/ - school finder
    path('api/', include('api.urls')),
    path('', include('lessons.urls')),  # Frontend HTML pages
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [
    re_path(r'^.*$', custom_404),
]
