from django.urls import path
from . import views

urlpatterns = [
    path('subcategories/', views.SubcategoryListCreateView.as_view(), name='subcategory-list-create'),
    path('subcategories/<int:pk>/', views.SubcategoryDetailView.as_view(), name='subcategory-detail'),
    path('', views.CategoryCreateListView.as_view(), name='category-create-list'),
    path('<int:pk>/', views.CategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),
]
