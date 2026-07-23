import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .forms import ClienteForm, CuentaCorrienteForm, ProductoForm, VentaDiariaForm
from .models import Cliente, CuentaCorriente, Producto, VentaDiaria, VentaItem


logger = logging.getLogger(__name__)
CENT = Decimal('0.01')



def catalogo_publico(request):
    productos = Producto.objects.filter(
        activo_en_catalogo=True,
        stock_actual__gt=0,
    ).order_by('nombre')
    return render(
        request,
        'despensa/catalogo.html',
        {
            'productos': productos,
            'whatsapp_phone': settings.WHATSAPP_PHONE,
        },
    )


@login_required
def gestion_dashboard(request):
    productos = Producto.objects.all()
    clientes = Cliente.objects.all()
    ventas_total = VentaDiaria.objects.aggregate(
        total=Coalesce(Sum('monto_total'), Decimal('0.00'))
    )['total']
    saldo_total = sum((cliente.saldo_total() for cliente in clientes), Decimal('0.00'))

    return render(
        request,
        'despensa/gestion/dashboard.html',
        {
            'productos_total': productos.count(),
            'productos_bajo_stock': productos.filter(stock_actual__lte=F('stock_minimo')).count(),
            'clientes_total': clientes.count(),
            'ventas_total': ventas_total,
            'saldo_total': saldo_total,
            'ultimos_movimientos': CuentaCorriente.objects.select_related('cliente')[:6],
            'ultimas_ventas': VentaDiaria.objects.all()[:6],
        },
    )


@login_required
def producto_lista(request):
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.all()
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(codigo_barras__icontains=query))
    return render(request, 'despensa/gestion/producto_lista.html', {'productos': productos, 'query': query})


@login_required
def producto_formulario(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk) if pk else None
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto guardado.')
            return redirect('despensa:producto_lista')
    else:
        form = ProductoForm(instance=producto)
    return render(
        request,
        'despensa/gestion/formulario.html',
        {
            'form': form,
            'titulo': 'Editar producto' if producto else 'Nuevo producto',
            'volver_url': 'despensa:producto_lista',
        },
    )


@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado correctamente.')
    return redirect('despensa:producto_lista')


@login_required
def cliente_lista(request):
    query = request.GET.get('q', '').strip()
    clientes = Cliente.objects.all()
    if query:
        clientes = clientes.filter(Q(nombre__icontains=query) | Q(telefono__icontains=query))
    return render(request, 'despensa/gestion/cliente_lista.html', {'clientes': clientes, 'query': query})


@login_required
def cliente_formulario(request, pk=None):
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, 'Cliente guardado.')
            return redirect('despensa:cliente_detalle', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(
        request,
        'despensa/gestion/formulario.html',
        {
            'form': form,
            'titulo': 'Editar cliente' if cliente else 'Nuevo cliente',
            'volver_url': 'despensa:cliente_lista',
        },
    )


@login_required
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = CuentaCorrienteForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.cliente = cliente
            movimiento.save()
            messages.success(request, 'Movimiento registrado.')
            return redirect('despensa:cliente_detalle', pk=cliente.pk)
    else:
        form = CuentaCorrienteForm()
        
    movimientos = cliente.movimientos.all().order_by('fecha', 'id')
    
    # Generar resumen en texto
    lines = []
    lines.append(f"*Resumen de Cuenta - Despensa LM*")
    lines.append(f"Cliente: {cliente.nombre}")
    lines.append(f"Fecha: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y')}")
    lines.append("")
    lines.append("Detalle de movimientos:")
    for mov in movimientos:
        fecha_str = mov.fecha.strftime('%d/%m/%Y')
        tipo = "Compra" if mov.tipo_movimiento == CuentaCorriente.TipoMovimiento.DEUDA else "Pago"
        monto_signo = "+" if mov.tipo_movimiento == CuentaCorriente.TipoMovimiento.DEUDA else "-"
        lines.append(f"• {fecha_str} | {tipo}: {mov.descripcion} ({monto_signo}${mov.monto})")
    
    lines.append("")
    lines.append(f"*Saldo Total Pendiente: ${cliente.saldo_total()}*")
    resumen_texto = "\n".join(lines)
    
    # Preparar link de WhatsApp
    telefono_limpio = "".join(filter(str.isdigit, cliente.telefono)) if cliente.telefono else ""
    if telefono_limpio and not telefono_limpio.startswith('54'):
        if len(telefono_limpio) == 10:
            telefono_limpio = "549" + telefono_limpio
            
    import urllib.parse
    whatsapp_url = f"https://wa.me/{telefono_limpio}?text={urllib.parse.quote(resumen_texto)}" if telefono_limpio else ""

    return render(
        request,
        'despensa/gestion/cliente_detalle.html',
        {
            'cliente': cliente,
            'form': form,
            'movimientos': cliente.movimientos.all().order_by('-fecha', '-id'),
            'resumen_texto': resumen_texto,
            'whatsapp_url': whatsapp_url,
        },
    )
@login_required
def movimiento_eliminar(request, pk):
    movimiento = get_object_or_404(CuentaCorriente, pk=pk)
    cliente_id = movimiento.cliente.pk
    if request.method == 'POST':
        movimiento.delete()
        messages.success(request, 'Movimiento eliminado correctamente.')
    return redirect('despensa:cliente_detalle', pk=cliente_id)


@login_required
def venta_lista(request):
    ventas = VentaDiaria.objects.all().order_by('-fecha', '-id')
    
    # Resumen de ventas
    total_general = ventas.aggregate(total=Coalesce(Sum('monto_total'), Decimal('0.00')))['total']
    
    # Agrupar por metodo de pago
    resumen_raw = (
        ventas.values('metodo_pago')
        .annotate(total=Coalesce(Sum('monto_total'), Decimal('0.00')))
        .order_by('metodo_pago')
    )
    choices_dict = dict(VentaDiaria.MetodoPago.choices)
    resumen_metodos = [
        {
            'nombre': choices_dict.get(item['metodo_pago'], item['metodo_pago']),
            'total': item['total']
        }
        for item in resumen_raw
    ]
    
    return render(
        request, 
        'despensa/gestion/venta_lista.html', 
        {
            'ventas': ventas,
            'total_general': total_general,
            'resumen_metodos': resumen_metodos,
        }
    )


@login_required
def venta_formulario(request):
    if request.method == 'POST':
        form = VentaDiariaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Venta registrada.')
            return redirect('despensa:venta_lista')
    else:
        form = VentaDiariaForm()
    return render(
        request,
        'despensa/gestion/formulario.html',
        {
            'form': form,
            'titulo': 'Nueva venta',
            'volver_url': 'despensa:venta_lista',
        },
    )


# --- API Endpoints para App Android ---

def api_login_required(view_func):
    @csrf_exempt
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'No autorizado'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({
            'success': True,
            'user': {
                'username': user.username,
                'email': user.email
            }
        })
    else:
        return JsonResponse({'success': False, 'error': 'Credenciales incorrectas'}, status=401)


@api_login_required
def api_producto_buscar(request):
    codigo = request.GET.get('codigo_barras', '').strip()
    if not codigo:
        return JsonResponse({'error': 'Código de barras no provisto'}, status=400)
    try:
        producto = Producto.objects.get(codigo_barras=codigo)
        return JsonResponse({
            'id': producto.id,
            'codigo_barras': producto.codigo_barras,
            'nombre': producto.nombre,
            'precio_costo': str(producto.precio_costo),
            'precio_venta': str(producto.precio_venta),
            'stock_actual': producto.stock_actual,
            'stock_minimo': producto.stock_minimo,
            'activo_en_catalogo': producto.activo_en_catalogo,
            'imagen_url': request.build_absolute_uri(producto.imagen.url) if producto.imagen else None
        })
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@api_login_required
def api_producto_lista(request):
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.all()
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(codigo_barras__icontains=query))
    
    data = []
    for prod in productos:
        data.append({
            'id': prod.id,
            'codigo_barras': prod.codigo_barras,
            'nombre': prod.nombre,
            'precio_costo': str(prod.precio_costo),
            'precio_venta': str(prod.precio_venta),
            'stock_actual': prod.stock_actual,
            'stock_minimo': prod.stock_minimo,
            'activo_en_catalogo': prod.activo_en_catalogo,
            'imagen_url': request.build_absolute_uri(prod.imagen.url) if prod.imagen else None
        })
    return JsonResponse(data, safe=False)


@api_login_required
def api_producto_guardar(request, pk=None):
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    producto = None
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    codigo = data.get('codigo_barras', '').strip() or None
    if codigo:
        exists_query = Producto.objects.filter(codigo_barras=codigo)
        if producto:
            exists_query = exists_query.exclude(pk=producto.pk)
        if exists_query.exists():
            return JsonResponse({'error': 'Ya existe un producto con este código de barras'}, status=400)

    nombre = data.get('nombre')
    precio_costo = data.get('precio_costo')
    precio_venta = data.get('precio_venta')
    stock_actual = data.get('stock_actual')
    stock_minimo = data.get('stock_minimo', 5)
    activo_en_catalogo = data.get('activo_en_catalogo', True)

    if not producto and not nombre:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)

    try:
        if producto:
            if nombre is not None: producto.nombre = nombre
            if codigo is not None: producto.codigo_barras = codigo
            if precio_costo is not None: producto.precio_costo = Decimal(str(precio_costo))
            if precio_venta is not None: producto.precio_venta = Decimal(str(precio_venta))
            if stock_actual is not None: producto.stock_actual = int(stock_actual)
            if stock_minimo is not None: producto.stock_minimo = int(stock_minimo)
            if activo_en_catalogo is not None: producto.activo_en_catalogo = bool(activo_en_catalogo)
            producto.save()
        else:
            producto = Producto.objects.create(
                nombre=nombre,
                codigo_barras=codigo,
                precio_costo=Decimal(str(precio_costo or '0.00')),
                precio_venta=Decimal(str(precio_venta or '0.00')),
                stock_actual=int(stock_actual or 0),
                stock_minimo=int(stock_minimo),
                activo_en_catalogo=bool(activo_en_catalogo)
            )
    except Exception as e:
        return JsonResponse({'error': f'Error al guardar producto: {str(e)}'}, status=400)

    return JsonResponse({
        'id': producto.id,
        'codigo_barras': producto.codigo_barras,
        'nombre': producto.nombre,
        'precio_costo': str(producto.precio_costo),
        'precio_venta': str(producto.precio_venta),
        'stock_actual': producto.stock_actual,
        'stock_minimo': producto.stock_minimo,
        'activo_en_catalogo': producto.activo_en_catalogo,
        'imagen_url': request.build_absolute_uri(producto.imagen.url) if producto.imagen else None
    }, status=200 if pk else 201)


@api_login_required
def api_producto_eliminar(request, pk):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    producto = get_object_or_404(Producto, pk=pk)
    producto.delete()
    return JsonResponse({'success': True})


def _cliente_data(cliente):
    return {
        'id': cliente.id,
        'nombre': cliente.nombre,
        'telefono': cliente.telefono,
        'notas': cliente.notas,
        'saldo_actual': f'{cliente.saldo_total():.2f}',
    }


@api_login_required
def api_cliente_lista(request):
    return JsonResponse([_cliente_data(cliente) for cliente in Cliente.objects.all()], safe=False)


@api_login_required
def api_cliente_guardar(request, pk=None):
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nombre = str(data.get('nombre', '')).strip()
    if not nombre:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)

    cliente = get_object_or_404(Cliente, pk=pk) if pk else Cliente()
    cliente.nombre = nombre
    cliente.telefono = str(data.get('telefono', '')).strip()
    if 'notas' in data:
        cliente.notas = str(data.get('notas') or '').strip()
    cliente.save()
    return JsonResponse(_cliente_data(cliente), status=200 if pk else 201)


@api_login_required
def api_cliente_movimientos(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'GET':
        movimientos = [
            {
                'id': movimiento.id,
                'fecha': timezone.localtime(movimiento.fecha).isoformat(),
                'tipo_movimiento': movimiento.tipo_movimiento,
                'monto': str(movimiento.monto),
                'descripcion': movimiento.descripcion,
            }
            for movimiento in cliente.movimientos.all()
        ]
        return JsonResponse({
            'cliente': _cliente_data(cliente),
            'movimientos': movimientos,
        })

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        monto = Decimal(str(data.get('monto')))
    except (json.JSONDecodeError, TypeError, ValueError, ArithmeticError):
        return JsonResponse({'error': 'El monto no es válido'}, status=400)

    tipo = data.get('tipo_movimiento')
    if tipo not in dict(CuentaCorriente.TipoMovimiento.choices):
        return JsonResponse({'error': 'Tipo de movimiento inválido'}, status=400)
    if monto <= 0:
        return JsonResponse({'error': 'El monto debe ser mayor que cero'}, status=400)

    movimiento = CuentaCorriente.objects.create(
        cliente=cliente,
        tipo_movimiento=tipo,
        monto=monto,
        descripcion=str(data.get('descripcion', '')).strip(),
    )
    return JsonResponse({
        'id': movimiento.id,
        'saldo_actual': f'{cliente.saldo_total():.2f}',
    }, status=201)


@api_login_required
def api_venta_crear(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    operacion_id = None
    operacion_id_raw = data.get('operacion_id')
    if operacion_id_raw:
        try:
            operacion_id = UUID(str(operacion_id_raw))
        except (TypeError, ValueError, AttributeError):
            return JsonResponse({'error': 'Identificador de operación inválido'}, status=400)

        venta_existente = VentaDiaria.objects.filter(operacion_id=operacion_id).first()
        if venta_existente:
            return _venta_response(venta_existente, duplicada=True)

    fecha_raw = data.get('fecha')
    try:
        fecha_operacion = date.fromisoformat(str(fecha_raw))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'La fecha debe usar el formato AAAA-MM-DD'}, status=400)

    metodo_pago = data.get('metodo_pago')
    notas = str(data.get('notas') or '').strip()
    cliente_id = data.get('cliente_id')
    items = data.get('items', [])

    if not metodo_pago:
        return JsonResponse({'error': 'El método de pago es obligatorio'}, status=400)
    if metodo_pago not in dict(VentaDiaria.MetodoPago.choices):
        return JsonResponse({'error': 'Método de pago inválido'}, status=400)
    if metodo_pago == 'FIADO' and not cliente_id:
        return JsonResponse({'error': 'Se requiere un cliente para compras fiadas'}, status=400)
    if not isinstance(items, list) or not items:
        return JsonResponse({'error': 'La venta debe incluir al menos un producto'}, status=400)

    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

    cantidades = {}
    precios = {}
    usa_precios_snapshot = True
    for item in items:
        if not isinstance(item, dict):
            return JsonResponse({'error': 'Formato de producto inválido'}, status=400)
        try:
            producto_id = int(item.get('producto_id'))
            cantidad = int(item.get('cantidad'))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Producto o cantidad inválidos'}, status=400)
        if cantidad <= 0:
            return JsonResponse({'error': 'Las cantidades deben ser mayores que cero'}, status=400)

        precio_raw = item.get('precio_unitario')
        if precio_raw is None:
            usa_precios_snapshot = False
        else:
            try:
                precio = Decimal(str(precio_raw)).quantize(CENT)
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({'error': 'Precio unitario inválido'}, status=400)
            if precio < 0:
                return JsonResponse({'error': 'El precio unitario no puede ser negativo'}, status=400)
            if producto_id in precios and precios[producto_id] != precio:
                return JsonResponse({'error': 'Un producto no puede tener dos precios en la misma venta'}, status=400)
            precios[producto_id] = precio

        cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad

    try:
        monto_declarado = Decimal(str(data.get('monto_total'))).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'error': 'Monto total inválido'}, status=400)

    try:
        with transaction.atomic():
            if operacion_id:
                venta_existente = VentaDiaria.objects.select_for_update().filter(
                    operacion_id=operacion_id
                ).first()
                if venta_existente:
                    return _venta_response(venta_existente, duplicada=True)

            productos = {
                producto.id: producto
                for producto in Producto.objects.select_for_update().filter(pk__in=cantidades)
            }
            faltantes = sorted(set(cantidades) - set(productos))
            if faltantes:
                return JsonResponse(
                    {'error': 'Uno de los productos provistos no existe', 'productos': faltantes},
                    status=400,
                )

            items_preparados = []
            monto_calculado = Decimal('0.00')
            for producto_id, cantidad in cantidades.items():
                producto = productos[producto_id]
                if producto.stock_actual < cantidad:
                    return JsonResponse(
                        {
                            'error': f'Stock insuficiente para {producto.nombre}',
                            'producto_id': producto.id,
                            'stock_disponible': producto.stock_actual,
                        },
                        status=409,
                    )

                precio_unitario = precios.get(producto_id, producto.precio_venta).quantize(CENT)
                subtotal = (precio_unitario * cantidad).quantize(CENT)
                monto_calculado += subtotal
                items_preparados.append((producto, cantidad, precio_unitario, subtotal))

            monto_calculado = monto_calculado.quantize(CENT)
            if monto_calculado <= 0:
                return JsonResponse({'error': 'El total calculado debe ser mayor que cero'}, status=400)
            if usa_precios_snapshot and monto_declarado != monto_calculado:
                return JsonResponse(
                    {
                        'error': 'El total enviado no coincide con los productos',
                        'monto_calculado': str(monto_calculado),
                    },
                    status=409,
                )

            venta = VentaDiaria.objects.create(
                fecha=fecha_operacion,
                operacion_id=operacion_id,
                cliente=cliente,
                monto_total=monto_calculado,
                metodo_pago=metodo_pago,
                notas=notas or 'Venta desde App Móvil',
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

            if metodo_pago == 'FIADO' and cliente:
                CuentaCorriente.objects.create(
                    cliente=cliente,
                    tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA,
                    monto=monto_calculado,
                    descripcion=notas or 'Compra fiada (App Móvil)',
                )

            for producto, cantidad, _, _ in items_preparados:
                producto.stock_actual -= cantidad
                producto.save(update_fields=['stock_actual', 'actualizado'])

            return _venta_response(venta, creada=True)
    except IntegrityError:
        if operacion_id:
            venta_existente = VentaDiaria.objects.filter(operacion_id=operacion_id).first()
            if venta_existente:
                return _venta_response(venta_existente, duplicada=True)
        logger.exception('Error de integridad al registrar una venta')
        return JsonResponse({'error': 'No se pudo registrar la venta'}, status=409)
    except Exception:
        logger.exception('Error inesperado al procesar una venta')
        return JsonResponse({'error': 'Error interno al procesar la venta'}, status=500)


def _venta_response(venta, creada=False, duplicada=False):
    response_data = {
        'success': True,
        'venta_id': venta.id,
        'operacion_id': str(venta.operacion_id) if venta.operacion_id else None,
        'monto_total': str(venta.monto_total),
        'duplicada': duplicada,
    }
    if venta.cliente_id:
        response_data['nuevo_saldo_cliente'] = str(venta.cliente.saldo_total())
    return JsonResponse(response_data, status=201 if creada else 200)
