from decimal import Decimal

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
