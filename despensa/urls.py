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
    path('gestion/productos/cargar-boleta/', views.boleta_carga, name='boleta_carga'),
    path('gestion/productos/nuevo/', views.producto_formulario, name='producto_nuevo'),
    path('gestion/productos/<int:pk>/editar/', views.producto_formulario, name='producto_editar'),
    path('gestion/productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('gestion/clientes/', views.cliente_lista, name='cliente_lista'),
    path('gestion/clientes/nuevo/', views.cliente_formulario, name='cliente_nuevo'),
    path('gestion/clientes/<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('gestion/clientes/<int:pk>/editar/', views.cliente_formulario, name='cliente_editar'),
    path('gestion/movimientos/<int:pk>/eliminar/', views.movimiento_eliminar, name='movimiento_eliminar'),
    path('gestion/ventas/', views.venta_lista, name='venta_lista'),
    path('gestion/ventas/nueva/', views.venta_formulario, name='venta_nueva'),

    # API Endpoints para App Android
    path('api/login/', views.api_login, name='api_login'),
    path('api/productos/buscar/', views.api_producto_buscar, name='api_producto_buscar'),
    path('api/productos/', views.api_producto_lista, name='api_producto_lista'),
    path('api/productos/guardar/', views.api_producto_guardar, name='api_producto_crear'),
    path('api/productos/<int:pk>/editar/', views.api_producto_guardar, name='api_producto_editar'),
    path('api/productos/<int:pk>/eliminar/', views.api_producto_eliminar, name='api_producto_eliminar'),
    path('api/clientes/', views.api_cliente_lista, name='api_cliente_lista'),
    path('api/clientes/guardar/', views.api_cliente_guardar, name='api_cliente_crear'),
    path('api/clientes/<int:pk>/editar/', views.api_cliente_guardar, name='api_cliente_editar'),
    path('api/clientes/<int:pk>/movimientos/', views.api_cliente_movimientos, name='api_cliente_movimientos'),
    path('api/ventas/', views.api_venta_crear, name='api_venta_crear'),
]
