from django.urls import path
from . import views

urlpatterns = [
    path('', views.ApiStatsView.as_view(), name='stats-view'),
]
