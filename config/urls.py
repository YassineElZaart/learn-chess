"""
URL configuration for Jeffy Academy project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('editor/', include('board_editor.urls')),
    path('lessons/', include('lessons.urls')),
    path('game/', include('gameplay.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = "Jeffy Academy Administration"
admin.site.site_title = "Jeffy Academy Admin"
admin.site.index_title = "Welcome to Jeffy Academy Administration"
