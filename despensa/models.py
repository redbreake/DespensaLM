from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class Producto(models.Model):
    codigo_barras = models.CharField('codigo de barras', max_length=64, unique=True, blank=True, null=True)
    nombre = models.CharField(max_length=160)
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    stock_actual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock_minimo = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    activo_en_catalogo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'producto'
        verbose_name_plural = 'productos'

    def __str__(self):
        return self.nombre

    @property
    def bajo_stock(self):
        return self.stock_actual <= self.stock_minimo


class Cliente(models.Model):
    nombre = models.CharField(max_length=160)
    telefono = models.CharField(max_length=40, blank=True)
    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return self.nombre

    def saldo_total(self):
        deudas = self.movimientos.filter(tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA).aggregate(
            total=Coalesce(Sum('monto'), Decimal('0.00'))
        )['total']
        pagos = self.movimientos.filter(tipo_movimiento=CuentaCorriente.TipoMovimiento.PAGO).aggregate(
            total=Coalesce(Sum('monto'), Decimal('0.00'))
        )['total']
        return deudas - pagos


class CuentaCorriente(models.Model):
    class TipoMovimiento(models.TextChoices):
        DEUDA = 'DEUDA', 'Compra fiada'
        PAGO = 'PAGO', 'Entrega de dinero'

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_movimiento = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    descripcion = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'movimiento de cuenta corriente'
        verbose_name_plural = 'movimientos de cuenta corriente'

    def __str__(self):
        return f'{self.cliente} - {self.get_tipo_movimiento_display()} - ${self.monto}'


class VentaDiaria(models.Model):
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
        DEBITO = 'DEBITO', 'Debito'
        FIADO = 'FIADO', 'Fiado'

    fecha = models.DateField('fecha', default=timezone.localdate)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    notas = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'venta diaria'
        verbose_name_plural = 'ventas diarias'

    def __str__(self):
        return f'{self.fecha} - {self.get_metodo_pago_display()} - ${self.monto_total}'
