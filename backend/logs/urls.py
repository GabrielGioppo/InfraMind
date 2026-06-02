from django.urls import path
from . import views

urlpatterns = [
    path('', views.LogCreateListView.as_view(), name='log-create-list'),
    path('<int:pk>/', views.LogRetrieveUpdateDestroyView.as_view(), name='log-detail'),
]
