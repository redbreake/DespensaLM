import hashlib
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
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


class ClienteQuerySet(models.QuerySet):
    def con_saldo(self):
        cero = Decimal('0.00')
        return self.annotate(
            _total_deudas=Coalesce(
                Sum(
                    'movimientos__monto',
                    filter=Q(movimientos__tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA),
                ),
                cero,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            _total_pagos=Coalesce(
                Sum(
                    'movimientos__monto',
                    filter=Q(movimientos__tipo_movimiento=CuentaCorriente.TipoMovimiento.PAGO),
                ),
                cero,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        ).annotate(
            saldo_anotado=ExpressionWrapper(
                F('_total_deudas') - F('_total_pagos'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )


class Cliente(models.Model):
    nombre = models.CharField(max_length=160)
    telefono = models.CharField(max_length=40, blank=True)
    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    objects = ClienteQuerySet.as_manager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return self.nombre

    def saldo_total(self):
        if hasattr(self, 'saldo_anotado') and self.saldo_anotado is not None:
            return self.saldo_anotado
        resumen = self.movimientos.aggregate(
            deudas=Coalesce(
                Sum('monto', filter=Q(tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA)),
                Decimal('0.00'),
            ),
            pagos=Coalesce(
                Sum('monto', filter=Q(tipo_movimiento=CuentaCorriente.TipoMovimiento.PAGO)),
                Decimal('0.00'),
            ),
        )
        return resumen['deudas'] - resumen['pagos']


class CuentaCorriente(models.Model):
    class TipoMovimiento(models.TextChoices):
        DEUDA = 'DEUDA', 'Compra fiada'
        PAGO = 'PAGO', 'Entrega de dinero'

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_movimiento = models.CharField(max_length=10, choices=TipoMovimiento.choices, default=TipoMovimiento.DEUDA)
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
    operacion_id = models.UUIDField(
        'identificador de operación',
        unique=True,
        blank=True,
        null=True,
        editable=False,
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name='ventas',
        blank=True,
        null=True,
    )
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    notas = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'venta diaria'
        verbose_name_plural = 'ventas diarias'

    def __str__(self):
        return f'{self.fecha} - {self.get_metodo_pago_display()} - ${self.monto_total}'


class VentaItem(models.Model):
    venta = models.ForeignKey(VentaDiaria, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        related_name='items_vendidos',
        blank=True,
        null=True,
    )
    nombre_producto = models.CharField(max_length=160)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'artículo de venta'
        verbose_name_plural = 'artículos de venta'

    def __str__(self):
        return f'{self.cantidad} x {self.nombre_producto} - ${self.subtotal}'


class ApiToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_tokens',
    )
    nombre = models.CharField(max_length=100, default='App Android')
    prefijo = models.CharField(max_length=12, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    creado = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'token de API'
        verbose_name_plural = 'tokens de API'

    def __str__(self):
        estado = 'activo' if self.activo else 'revocado'
        return f'{self.user} ({self.prefijo}...) - {estado}'

    @staticmethod
    def hash_token(raw_token):
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @classmethod
    def crear_para_usuario(cls, user, nombre='App Android'):
        raw_token = secrets.token_urlsafe(32)
        token = cls.objects.create(
            user=user,
            nombre=nombre,
            prefijo=raw_token[:12],
            token_hash=cls.hash_token(raw_token),
        )
        return token, raw_token

    @classmethod
    def autenticar(cls, raw_token):
        if not raw_token:
            return None
        token = (
            cls.objects.select_related('user')
            .filter(token_hash=cls.hash_token(raw_token), activo=True, user__is_active=True)
            .first()
        )
        if token:
            cls.objects.filter(pk=token.pk).update(ultimo_uso=timezone.now())
        return token
