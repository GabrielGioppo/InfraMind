from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageCreateListView.as_view(), name='image-create-list'),
    path('<int:pk>/', views.ImageRetrieveUpdateDestroyView.as_view(), name='image-detail'),
    path('anonymous/', views.create_anonymous_image, name='image-anonymous-create'),
]
