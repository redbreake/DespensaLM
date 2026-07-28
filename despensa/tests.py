from decimal import Decimal
import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, CuentaCorriente, Producto, VentaDiaria, VentaItem


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

    def test_catalogo_incluye_acceso_movil_persistente_al_carrito(self):
        response = self.client.get(reverse('despensa:catalogo'))
        html = response.content.decode('utf-8')

        self.assertContains(response, 'class="mobile-cart-bar"')
        self.assertContains(response, 'id="cart-panel"')
        self.assertEqual(html.count('aria-controls="cart-panel"'), 2)


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


class ApiVentaTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='operador', password='clave-test')
        self.client.force_login(self.user)
        self.producto = Producto.objects.create(
            nombre='Yerba',
            precio_costo=Decimal('1000.00'),
            precio_venta=Decimal('1500.00'),
            stock_actual=5,
        )
        self.cliente = Cliente.objects.create(nombre='María')
        self.operacion_id = str(uuid4())

    def payload(self, **overrides):
        data = {
            'operacion_id': self.operacion_id,
            'fecha': '2026-07-20',
            'monto_total': '3000.00',
            'metodo_pago': 'EFECTIVO',
            'notas': 'Venta de prueba',
            'cliente_id': None,
            'items': [
                {
                    'producto_id': self.producto.id,
                    'cantidad': 2,
                    'precio_unitario': '1500.00',
                }
            ],
        }
        data.update(overrides)
        return data

    def registrar(self, payload):
        return self.client.post(
            reverse('despensa:api_venta_crear'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_crea_venta_detallada_con_fecha_original_y_descuenta_stock(self):
        response = self.registrar(self.payload())

        self.assertEqual(response.status_code, 201)
        venta = VentaDiaria.objects.get()
        item = VentaItem.objects.get()
        self.producto.refresh_from_db()

        self.assertEqual(str(venta.operacion_id), self.operacion_id)
        self.assertEqual(venta.fecha.isoformat(), '2026-07-20')
        self.assertEqual(venta.monto_total, Decimal('3000.00'))
        self.assertEqual(item.producto, self.producto)
        self.assertEqual(item.nombre_producto, 'Yerba')
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(item.precio_unitario, Decimal('1500.00'))
        self.assertEqual(item.subtotal, Decimal('3000.00'))
        self.assertEqual(self.producto.stock_actual, 3)

    def test_reintento_idempotente_no_duplica_venta_stock_ni_fiado(self):
        payload = self.payload(
            metodo_pago='FIADO',
            cliente_id=self.cliente.id,
        )

        primera = self.registrar(payload)
        segunda = self.registrar(payload)
        self.producto.refresh_from_db()

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 200)
        self.assertTrue(segunda.json()['duplicada'])
        self.assertEqual(VentaDiaria.objects.count(), 1)
        self.assertEqual(VentaItem.objects.count(), 1)
        self.assertEqual(CuentaCorriente.objects.count(), 1)
        self.assertEqual(self.producto.stock_actual, 3)
        self.assertEqual(self.cliente.saldo_total(), Decimal('3000.00'))

    def test_stock_insuficiente_rechaza_toda_la_venta(self):
        otro = Producto.objects.create(
            nombre='Azúcar',
            precio_costo=Decimal('500.00'),
            precio_venta=Decimal('800.00'),
            stock_actual=0,
        )
        payload = self.payload(
            monto_total='3800.00',
            items=[
                {
                    'producto_id': self.producto.id,
                    'cantidad': 2,
                    'precio_unitario': '1500.00',
                },
                {
                    'producto_id': otro.id,
                    'cantidad': 1,
                    'precio_unitario': '800.00',
                },
            ],
        )

        response = self.registrar(payload)
        self.producto.refresh_from_db()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(VentaDiaria.objects.count(), 0)
        self.assertEqual(VentaItem.objects.count(), 0)
        self.assertEqual(self.producto.stock_actual, 5)

    def test_total_inconsistente_se_rechaza_sin_modificar_datos(self):
        response = self.registrar(self.payload(monto_total='1.00'))
        self.producto.refresh_from_db()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['monto_calculado'], '3000.00')
        self.assertEqual(VentaDiaria.objects.count(), 0)
        self.assertEqual(self.producto.stock_actual, 5)

    def test_items_repetidos_se_agrupan_antes_de_validar_stock(self):
        response = self.registrar(self.payload(
            items=[
                {
                    'producto_id': self.producto.id,
                    'cantidad': 1,
                    'precio_unitario': '1500.00',
                },
                {
                    'producto_id': self.producto.id,
                    'cantidad': 1,
                    'precio_unitario': '1500.00',
                },
            ],
        ))
        self.producto.refresh_from_db()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(VentaItem.objects.get().cantidad, 2)
        self.assertEqual(self.producto.stock_actual, 3)

    def test_cliente_anterior_sin_uuid_usa_precio_actual_del_servidor(self):
        payload = self.payload()
        payload.pop('operacion_id')
        payload['monto_total'] = '10.00'
        payload['items'][0].pop('precio_unitario')

        response = self.registrar(payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['monto_total'], '3000.00')
        self.assertIsNone(VentaDiaria.objects.get().operacion_id)

    def test_fecha_invalida_se_rechaza(self):
        response = self.registrar(self.payload(fecha='20/07/2026'))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(VentaDiaria.objects.count(), 0)
