from django.urls import path

from . import views

app_name = 'despensa'

urlpatterns = [
    path('', views.catalogo_publico, name='catalogo'),
]
