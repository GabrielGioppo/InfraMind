from django.urls import path
from authentication.views import login_by_email, password_reset_request, password_reset_confirm

urlpatterns = [
    path('login/', login_by_email, name='login-by-email'),
    path('password-reset/', password_reset_request, name='password-reset'),
    path('password-reset/confirm/', password_reset_confirm, name='password-reset-confirm'),
]
