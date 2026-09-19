from django.urls import path
from . import views

urlpatterns = [
    path('', views.OccurrenceCreateListView.as_view(), name='occurrence-create-list'),
    path('<int:pk>/', views.OccurrenceRetrieveUpdateDestroyView.as_view(), name='occurrence-detail'),
    path('nearby/<str:lat>/<str:lng>/', views.nearby_occurrences, name='nearby-occurrences'),
    path('geocode/', views.geocode_address, name='geocode-address'),
    path('anonymous/', views.create_anonymous_occurrence, name='occurrence-anonymous-create'),
    path('anonymous/claim/', views.claim_anonymous_occurrences, name='occurrence-anonymous-claim'),
]
