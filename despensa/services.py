from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from .models import Cliente, CuentaCorriente, Producto, VentaDiaria, VentaItem

CENT = Decimal('0.01')


class VentaError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = {'error': message, **(payload or {})}


def registrar_venta_transaccional(
    *,
    fecha_operacion,
    metodo_pago,
    items_raw,
    notas='',
    cliente_id=None,
    operacion_id=None,
    monto_declarado=None,
    origen_default='Venta desde App Móvil',
    fiado_default='Compra fiada (App Móvil)',
):
    if operacion_id:
        venta_existente = VentaDiaria.objects.filter(operacion_id=operacion_id).first()
        if venta_existente:
            return venta_existente, False, True

    if not metodo_pago:
        raise VentaError('El método de pago es obligatorio', status_code=400)
    if metodo_pago not in dict(VentaDiaria.MetodoPago.choices):
        raise VentaError('Método de pago inválido', status_code=400)
    if metodo_pago == VentaDiaria.MetodoPago.FIADO and not cliente_id:
        raise VentaError('Se requiere un cliente para compras fiadas', status_code=400)
    if not isinstance(items_raw, list) or not items_raw:
        raise VentaError('La venta debe incluir al menos un producto', status_code=400)

    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            raise VentaError('Cliente no encontrado', status_code=404)

    cantidades = {}
    precios = {}
    usa_precios_snapshot = True
    for item in items_raw:
        if not isinstance(item, dict):
            raise VentaError('Formato de producto inválido', status_code=400)
        try:
            producto_id = int(item.get('producto_id'))
            cantidad = int(item.get('cantidad'))
        except (TypeError, ValueError):
            raise VentaError('Producto o cantidad inválidos', status_code=400)
        if cantidad <= 0:
            raise VentaError('Las cantidades deben ser mayores que cero', status_code=400)

        precio_raw = item.get('precio_unitario')
        if precio_raw is None or precio_raw == '':
            usa_precios_snapshot = False
        else:
            try:
                precio = Decimal(str(precio_raw)).quantize(CENT)
            except (InvalidOperation, TypeError, ValueError):
                raise VentaError('Precio unitario inválido', status_code=400)
            if precio < 0:
                raise VentaError('El precio unitario no puede ser negativo', status_code=400)
            if producto_id in precios and precios[producto_id] != precio:
                raise VentaError(
                    'Un producto no puede tener dos precios en la misma venta',
                    status_code=400,
                )
            precios[producto_id] = precio

        cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad

    notas_limpias = str(notas or '').strip()

    try:
        with transaction.atomic():
            if operacion_id:
                venta_existente = VentaDiaria.objects.select_for_update().filter(
                    operacion_id=operacion_id
                ).first()
                if venta_existente:
                    return venta_existente, False, True

            productos = {
                producto.id: producto
                for producto in Producto.objects.select_for_update().filter(pk__in=cantidades)
            }
            faltantes = sorted(set(cantidades) - set(productos))
            if faltantes:
                raise VentaError(
                    'Uno de los productos provistos no existe',
                    status_code=400,
                    payload={'productos': faltantes},
                )

            items_preparados = []
            monto_calculado = Decimal('0.00')
            for producto_id, cantidad in cantidades.items():
                producto = productos[producto_id]
                if producto.stock_actual < cantidad:
                    raise VentaError(
                        f'Stock insuficiente para {producto.nombre}',
                        status_code=409,
                        payload={
                            'producto_id': producto.id,
                            'stock_disponible': producto.stock_actual,
                        },
                    )

                precio_unitario = precios.get(producto_id, producto.precio_venta).quantize(CENT)
                subtotal = (precio_unitario * cantidad).quantize(CENT)
                monto_calculado += subtotal
                items_preparados.append((producto, cantidad, precio_unitario, subtotal))

            monto_calculado = monto_calculado.quantize(CENT)
            if monto_calculado <= 0:
                raise VentaError('El total calculado debe ser mayor que cero', status_code=400)
            if (
                usa_precios_snapshot
                and monto_declarado is not None
                and monto_declarado != monto_calculado
            ):
                raise VentaError(
                    'El total enviado no coincide con los productos',
                    status_code=409,
                    payload={'monto_calculado': str(monto_calculado)},
                )

            venta = VentaDiaria.objects.create(
                fecha=fecha_operacion,
                operacion_id=operacion_id,
                cliente=cliente,
                monto_total=monto_calculado,
                metodo_pago=metodo_pago,
                notas=notas_limpias or origen_default,
            )

            VentaItem.objects.bulk_create([
                VentaItem(
                    venta=venta,
                    producto=producto,
                    nombre_producto=producto.nombre,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal,
                )
                for producto, cantidad, precio_unitario, subtotal in items_preparados
            ])

            if metodo_pago == VentaDiaria.MetodoPago.FIADO and cliente:
                CuentaCorriente.objects.create(
                    cliente=cliente,
                    tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA,
                    monto=monto_calculado,
                    descripcion=notas_limpias or fiado_default,
                )

            for producto, cantidad, _, _ in items_preparados:
                producto.stock_actual -= cantidad
                producto.save(update_fields=['stock_actual', 'actualizado'])

            return venta, True, False
    except IntegrityError:
        if operacion_id:
            venta_existente = VentaDiaria.objects.filter(operacion_id=operacion_id).first()
            if venta_existente:
                return venta_existente, False, True
        raise VentaError('No se pudo registrar la venta', status_code=409)
