from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserCreateView.as_view(), name='user-register'),
    path('', views.UserListView.as_view(), name='user-list'),
    path('<int:pk>/', views.UserRetrieveUpdateDestroyView.as_view(), name='user-detail'),
]
