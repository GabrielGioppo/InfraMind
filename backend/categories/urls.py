from django.urls import path
from . import views

urlpatterns = [
    path('', views.CategoryCreateListView.as_view(), name='category-create-list'),
    path('<int:pk>/', views.CategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),
]
