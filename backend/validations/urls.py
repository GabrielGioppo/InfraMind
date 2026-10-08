from django.urls import path
from . import views

urlpatterns = [
    path('', views.ValidationCreateListView.as_view(), name='validation-create-list'),
    path('occurrence/<int:occurrence_id>/', views.validate_occurrence, name='validate-occurrence'),
    path('ai-analyze/', views.ai_analyze_occurrence, name='ai-analyze-occurrence'),
    path('ai-prioritized/', views.admin_ai_prioritized_occurrences, name='ai-prioritized-occurrences'),
]
