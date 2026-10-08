from django.urls import path
from . import views

urlpatterns = [
    path('reverse/', views.reverse_geocode, name='geo-reverse'),
    path('search/',  views.forward_geocode, name='geo-search'),
]
