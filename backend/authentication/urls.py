from django.urls import path
from authentication.views import login_by_email

urlpatterns = [
    path('login/', login_by_email, name='login-by-email'),
]
