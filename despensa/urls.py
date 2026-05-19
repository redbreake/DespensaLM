from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'despensa'

urlpatterns = [
    path('', views.catalogo_publico, name='catalogo'),
    path('ingresar/', auth_views.LoginView.as_view(template_name='despensa/gestion/login.html'), name='login'),
    path('salir/', auth_views.LogoutView.as_view(next_page='despensa:catalogo'), name='logout'),
    path('gestion/', views.gestion_dashboard, name='gestion_dashboard'),
    path('gestion/productos/', views.producto_lista, name='producto_lista'),
    path('gestion/productos/nuevo/', views.producto_formulario, name='producto_nuevo'),
    path('gestion/productos/<int:pk>/editar/', views.producto_formulario, name='producto_editar'),
    path('gestion/productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('gestion/clientes/', views.cliente_lista, name='cliente_lista'),
    path('gestion/clientes/nuevo/', views.cliente_formulario, name='cliente_nuevo'),
    path('gestion/clientes/<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('gestion/clientes/<int:pk>/editar/', views.cliente_formulario, name='cliente_editar'),
    path('gestion/ventas/', views.venta_lista, name='venta_lista'),
    path('gestion/ventas/nueva/', views.venta_formulario, name='venta_nueva'),
]
