from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, CuentaCorriente, Producto


class ClienteTests(TestCase):
    def test_saldo_total_resta_pagos_a_deudas(self):
        cliente = Cliente.objects.create(nombre='Maria')
        CuentaCorriente.objects.create(
            cliente=cliente,
            tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA,
            monto=Decimal('1500.00'),
            descripcion='Compra fiada',
        )
        CuentaCorriente.objects.create(
            cliente=cliente,
            tipo_movimiento=CuentaCorriente.TipoMovimiento.PAGO,
            monto=Decimal('500.00'),
            descripcion='Entrega a cuenta',
        )

        self.assertEqual(cliente.saldo_total(), Decimal('1000.00'))


class CatalogoTests(TestCase):
    def test_catalogo_muestra_solo_productos_activos_con_stock(self):
        visible = Producto.objects.create(
            nombre='Yerba',
            precio_costo=Decimal('1000.00'),
            precio_venta=Decimal('1500.00'),
            stock_actual=3,
        )
        Producto.objects.create(
            nombre='Sin stock',
            precio_costo=Decimal('1000.00'),
            precio_venta=Decimal('1500.00'),
            stock_actual=0,
        )
        Producto.objects.create(
            nombre='Inactivo',
            precio_costo=Decimal('1000.00'),
            precio_venta=Decimal('1500.00'),
            stock_actual=3,
            activo_en_catalogo=False,
        )

        response = self.client.get(reverse('despensa:catalogo'))

        self.assertContains(response, visible.nombre)
        self.assertNotContains(response, 'Sin stock')
        self.assertNotContains(response, 'Inactivo')

    def test_catalogo_tiene_acceso_al_login(self):
        response = self.client.get(reverse('despensa:catalogo'))

        self.assertContains(response, reverse('despensa:login'))


class GestionTests(TestCase):
    def test_gestion_requiere_login_y_luego_muestra_panel(self):
        response = self.client.get(reverse('despensa:gestion_dashboard'))
        self.assertEqual(response.status_code, 302)

        user_model = get_user_model()
        user_model.objects.create_user(username='admin', password='clave-test')
        self.client.login(username='admin', password='clave-test')

        response = self.client.get(reverse('despensa:gestion_dashboard'))
        self.assertContains(response, 'Panel de gestion')


class ApiAppTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='operador', password='clave-test')
        self.client.force_login(self.user)

    def test_permite_crear_editar_cliente_y_registrar_pago(self):
        response = self.client.post(
            reverse('despensa:api_cliente_crear'),
            data=json.dumps({'nombre': 'María', 'telefono': '3764000000', 'notas': 'Vecina'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        cliente_id = response.json()['id']

        response = self.client.put(
            reverse('despensa:api_cliente_editar', args=[cliente_id]),
            data=json.dumps({'nombre': 'María López', 'telefono': '3764000000', 'notas': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'María López')

        CuentaCorriente.objects.create(
            cliente_id=cliente_id,
            tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA,
            monto=Decimal('1200.00'),
        )
        response = self.client.post(
            reverse('despensa:api_cliente_movimientos', args=[cliente_id]),
            data=json.dumps({'tipo_movimiento': 'PAGO', 'monto': '500.00', 'descripcion': 'Entrega'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['saldo_actual'], '700.00')

        response = self.client.get(reverse('despensa:api_cliente_movimientos', args=[cliente_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['movimientos']), 2)

    def test_permite_eliminar_producto(self):
        producto = Producto.objects.create(
            nombre='Producto temporal',
            precio_costo=Decimal('10.00'),
            precio_venta=Decimal('20.00'),
        )

        response = self.client.delete(reverse('despensa:api_producto_eliminar', args=[producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Producto.objects.filter(pk=producto.id).exists())

    def test_api_rechaza_acceso_sin_sesion(self):
        self.client.logout()

        response = self.client.get(reverse('despensa:api_cliente_lista'))

        self.assertEqual(response.status_code, 401)
