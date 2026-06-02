from django.urls import path
from . import views

urlpatterns = [
    path('', views.FeedbackCreateListView.as_view(), name='feedback-create-list'),
    path('<int:pk>/', views.FeedbackRetrieveUpdateDestroyView.as_view(), name='feedback-detail'),
]
