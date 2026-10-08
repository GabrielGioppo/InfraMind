from django.urls import path
from . import views

urlpatterns = [
    path('<int:occurrence_id>/history/', views.OccurrenceHistoryListView.as_view(), name='occurrence-history'),
]
