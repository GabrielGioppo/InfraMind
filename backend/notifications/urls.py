from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificacaoListView.as_view(), name='notification-list'),
    path('process-deadlines/', views.processar_prazos_view, name='notification-process-deadlines'),
]
