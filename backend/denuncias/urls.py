from django.urls import path

from denuncias import views

urlpatterns = [
    path('', views.DenunciaListCreateView.as_view(), name='denuncia-list-create'),
    path('<int:pk>/', views.DenunciaStatusView.as_view(), name='denuncia-status'),
]
