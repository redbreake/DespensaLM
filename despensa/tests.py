from decimal import Decimal

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
