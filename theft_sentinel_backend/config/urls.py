"""
Main URL Configuration

"""
print("DASHBOARD URLS LOADED")

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # API endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/personnel/', include('apps.personnel.urls')),
    path('api/cameras/', include('apps.cameras.urls')),
    path('api/surveillance/', include('apps.surveillance.urls')),
    path('api/tracking/', include('apps.tracking.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/mobile/', include('apps.mobile.urls')),
    path('api/incidents/', include('apps.incidents.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/feedback/', include('apps.feedback.urls')),
    path('api/tenancy/', include('apps.tenancy.urls')),
    path('api/support/', include('apps.support.urls')),
    
    # AI Engine endpoints (NEW - ISOLATED)
    path('api/ai/', include('apps.ai_engine.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

