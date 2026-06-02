from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('admin/', admin.site.urls),

    
    path('authentication/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('authentication/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('authentication/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('authentication/', include('authentication.urls')),

    
    path('api/v1/users/', include('users.urls')),
    path('api/v1/categories/', include('categories.urls')),
    path('api/v1/occurrences/', include('occurrences.urls')),
    path('api/v1/occurrences/', include('history.urls')),
    path('api/v1/images/', include('images.urls')),
    path('api/v1/validations/', include('validations.urls')),
    path('api/v1/feedbacks/', include('feedbacks.urls')),
    path('api/v1/logs/', include('logs.urls')),
    path('api/v1/statistics/', include('statistics_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
