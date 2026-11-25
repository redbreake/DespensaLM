import json
import logging
import urllib.parse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from functools import wraps
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .forms import ClienteForm, CuentaCorrienteForm, ProductoForm, VentaDiariaForm
from .models import ApiToken, Cliente, CuentaCorriente, Producto, VentaDiaria, VentaItem
from .services import VentaError, registrar_venta_transaccional


logger = logging.getLogger(__name__)
CENT = Decimal('0.01')
PRECIO_REDONDEO = Decimal('100')
MAX_PRODUCTOS_BOLETA = 100
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60



def catalogo_publico(request):
    productos = Producto.objects.filter(
        activo_en_catalogo=True,
        stock_actual__gt=0,
        precio_venta__gt=0,
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
    ventas_total = VentaDiaria.objects.aggregate(
        total=Coalesce(Sum('monto_total'), Decimal('0.00'))
    )['total']
    resumen_fiado = CuentaCorriente.objects.aggregate(
        deudas=Coalesce(
            Sum('monto', filter=Q(tipo_movimiento=CuentaCorriente.TipoMovimiento.DEUDA)),
            Decimal('0.00'),
        ),
        pagos=Coalesce(
            Sum('monto', filter=Q(tipo_movimiento=CuentaCorriente.TipoMovimiento.PAGO)),
            Decimal('0.00'),
        ),
    )
    saldo_total = resumen_fiado['deudas'] - resumen_fiado['pagos']

    return render(
        request,
        'despensa/gestion/dashboard.html',
        {
            'productos_total': productos.count(),
            'productos_bajo_stock': productos.filter(stock_actual__lte=F('stock_minimo')).count(),
            'clientes_total': Cliente.objects.count(),
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


def _precio_con_margen(precio_costo, margen):
    precio = precio_costo * (Decimal('1') + margen / Decimal('100'))
    return (
        (precio / PRECIO_REDONDEO).to_integral_value(rounding=ROUND_CEILING)
        * PRECIO_REDONDEO
    ).quantize(CENT)


@login_required
def boleta_carga(request):
    items_iniciales = []

    if request.method == 'POST':
        try:
            items_iniciales = json.loads(request.POST.get('items', '[]'))
            margen = Decimal(request.POST.get('margen', '30'))
        except (json.JSONDecodeError, InvalidOperation, TypeError):
            messages.error(request, 'La información de la boleta no es válida.')
        else:
            errores = []
            items_limpios = []
            nombres_vistos = set()

            if not isinstance(items_iniciales, list) or not items_iniciales:
                errores.append('Agregá al menos un producto.')
            elif len(items_iniciales) > MAX_PRODUCTOS_BOLETA:
                errores.append(f'La boleta no puede superar {MAX_PRODUCTOS_BOLETA} productos.')

            if margen < 0 or margen > 500:
                errores.append('El margen debe estar entre 0 y 500 %.')

            if not errores:
                for posicion, item in enumerate(items_iniciales, start=1):
                    try:
                        nombre = str(item.get('nombre', '')).strip()
                        cantidad = int(item.get('cantidad', 0))
                        precio_costo = Decimal(str(item.get('precio_costo', '0'))).quantize(CENT)
                        precio_venta_raw = item.get('precio_venta')
                        precio_venta = (
                            Decimal(str(precio_venta_raw)).quantize(CENT)
                            if precio_venta_raw not in (None, '')
                            else _precio_con_margen(precio_costo, margen)
                        )
                    except (AttributeError, InvalidOperation, TypeError, ValueError):
                        errores.append(f'Fila {posicion}: revisá cantidad y precios.')
                        continue

                    nombre_clave = nombre.casefold()
                    if not nombre:
                        errores.append(f'Fila {posicion}: falta el nombre.')
                    elif nombre_clave in nombres_vistos:
                        errores.append(f'Fila {posicion}: el producto está repetido.')
                    elif cantidad <= 0:
                        errores.append(f'Fila {posicion}: la cantidad debe ser mayor que cero.')
                    elif precio_costo < 0 or precio_venta < 0:
                        errores.append(f'Fila {posicion}: los precios no pueden ser negativos.')
                    else:
                        nombres_vistos.add(nombre_clave)
                        items_limpios.append(
                            {
                                'nombre': nombre,
                                'cantidad': cantidad,
                                'precio_costo': precio_costo,
                                'precio_venta': precio_venta,
                            }
                        )

            if errores:
                for error in errores:
                    messages.error(request, error)
            else:
                creados = 0
                actualizados = 0
                unidades = 0

                with transaction.atomic():
                    for item in items_limpios:
                        producto = (
                            Producto.objects.select_for_update()
                            .filter(nombre__iexact=item['nombre'])
                            .first()
                        )
                        if producto:
                            producto.stock_actual += item['cantidad']
                            producto.precio_costo = item['precio_costo']
                            producto.precio_venta = item['precio_venta']
                            producto.save(
                                update_fields=(
                                    'stock_actual',
                                    'precio_costo',
                                    'precio_venta',
                                    'actualizado',
                                )
                            )
                            actualizados += 1
                        else:
                            Producto.objects.create(
                                nombre=item['nombre'],
                                precio_costo=item['precio_costo'],
                                precio_venta=item['precio_venta'],
                                stock_actual=item['cantidad'],
                                stock_minimo=5,
                                activo_en_catalogo=True,
                            )
                            creados += 1
                        unidades += item['cantidad']

                messages.success(
                    request,
                    (
                        f'Boleta cargada: {unidades} unidades, '
                        f'{creados} productos nuevos y {actualizados} actualizados.'
                    ),
                )
                return redirect('despensa:producto_lista')

    return render(
        request,
        'despensa/gestion/boleta_carga.html',
        {
            'productos_existentes': list(
                Producto.objects.order_by('nombre').values_list('nombre', flat=True)
            ),
            'items_iniciales': items_iniciales if isinstance(items_iniciales, list) else [],
            'margen_inicial': request.POST.get('margen', '30'),
        },
        status=400 if request.method == 'POST' else 200,
    )


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
    clientes = Cliente.objects.con_saldo()
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
    cliente = get_object_or_404(Cliente.objects.con_saldo(), pk=pk)
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

    movimientos_asc = list(cliente.movimientos.all().order_by('fecha', 'id'))
    saldo_actual = cliente.saldo_total()

    # Generar resumen en texto
    lines = []
    lines.append(f"*Resumen de Cuenta - Despensa LM*")
    lines.append(f"Cliente: {cliente.nombre}")
    lines.append(f"Fecha: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y')}")
    lines.append("")
    lines.append("Detalle de movimientos:")
    for mov in movimientos_asc:
        fecha_str = timezone.localtime(mov.fecha).strftime('%d/%m/%Y')
        tipo = "Compra" if mov.tipo_movimiento == CuentaCorriente.TipoMovimiento.DEUDA else "Pago"
        monto_signo = "+" if mov.tipo_movimiento == CuentaCorriente.TipoMovimiento.DEUDA else "-"
        lines.append(f"• {fecha_str} | {tipo}: {mov.descripcion} ({monto_signo}${mov.monto})")

    lines.append("")
    lines.append(f"*Saldo Total Pendiente: ${saldo_actual}*")
    resumen_texto = "\n".join(lines)

    # Preparar link de WhatsApp
    telefono_limpio = "".join(filter(str.isdigit, cliente.telefono)) if cliente.telefono else ""
    if telefono_limpio and not telefono_limpio.startswith('54'):
        if len(telefono_limpio) == 10:
            telefono_limpio = "549" + telefono_limpio

    whatsapp_url = f"https://wa.me/{telefono_limpio}?text={urllib.parse.quote(resumen_texto)}" if telefono_limpio else ""

    return render(
        request,
        'despensa/gestion/cliente_detalle.html',
        {
            'cliente': cliente,
            'form': form,
            'movimientos': list(reversed(movimientos_asc)),
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
    ventas = VentaDiaria.objects.select_related('cliente').prefetch_related('items').order_by('-fecha', '-id')
    
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
    items_iniciales = []
    fecha_inicial = timezone.localdate().isoformat()
    metodo_inicial = VentaDiaria.MetodoPago.EFECTIVO
    cliente_inicial = ''
    notas_inicial = ''
    status_code = 200

    if request.method == 'POST':
        fecha_inicial = request.POST.get('fecha', fecha_inicial)
        metodo_inicial = request.POST.get('metodo_pago', metodo_inicial)
        cliente_inicial = request.POST.get('cliente_id', '').strip()
        notas_inicial = request.POST.get('notas', '').strip()
        status_code = 400

        try:
            items_iniciales = json.loads(request.POST.get('items', '[]'))
            fecha_operacion = date.fromisoformat(str(fecha_inicial))
        except (json.JSONDecodeError, TypeError, ValueError):
            messages.error(request, 'Revisá la fecha y los productos de la venta.')
        else:
            try:
                venta, _, _ = registrar_venta_transaccional(
                    fecha_operacion=fecha_operacion,
                    metodo_pago=metodo_inicial,
                    items_raw=items_iniciales,
                    notas=notas_inicial,
                    cliente_id=int(cliente_inicial) if cliente_inicial else None,
                    origen_default='Venta en caja web',
                    fiado_default='Compra fiada (Caja web)',
                )
            except ValueError:
                messages.error(request, 'El cliente seleccionado no es válido.')
            except VentaError as exc:
                messages.error(request, exc.message)
                status_code = exc.status_code
            else:
                messages.success(request, f'Venta registrada por ${venta.monto_total}.')
                return redirect('despensa:venta_lista')

    productos_catalogo = [
        {
            'id': p.id,
            'nombre': p.nombre,
            'precio_venta': str(p.precio_venta),
            'stock_actual': p.stock_actual,
        }
        for p in Producto.objects.filter(stock_actual__gt=0, precio_venta__gt=0).order_by('nombre')
    ]

    return render(
        request,
        'despensa/gestion/venta_nueva.html',
        {
            'productos_catalogo': productos_catalogo,
            'clientes': Cliente.objects.order_by('nombre'),
            'metodos_pago': VentaDiaria.MetodoPago.choices,
            'items_iniciales': items_iniciales if isinstance(items_iniciales, list) else [],
            'fecha_inicial': fecha_inicial,
            'metodo_inicial': metodo_inicial,
            'cliente_inicial': cliente_inicial,
            'notas_inicial': notas_inicial,
        },
        status=status_code,
    )


# --- API Endpoints para App Android ---

def _extract_bearer_token(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '').strip()
    if auth_header.lower().startswith('bearer '):
        return auth_header[7:].strip()
    return None


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def api_login_required(view_func):
    @csrf_exempt
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        request.api_token = None
        raw_token = _extract_bearer_token(request)
        if raw_token is not None:
            token = ApiToken.autenticar(raw_token)
            if token is None:
                return JsonResponse({'error': 'Token inválido o revocado'}, status=401)
            request.user = token.user
            request.api_token = token
            return view_func(request, *args, **kwargs)

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
        if not isinstance(data, dict):
            raise TypeError
        username = str(data.get('username') or '').strip()
        password = str(data.get('password') or '')
        device_name = str(data.get('device_name') or 'App Android').strip()[:100] or 'App Android'
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    rate_key = f'api_login_fail:{_client_ip(request)}:{username.lower()}'
    attempts = cache.get(rate_key, 0)
    if attempts >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        return JsonResponse(
            {'success': False, 'error': 'Demasiados intentos fallidos. Esperá unos minutos.'},
            status=429,
        )

    user = authenticate(request, username=username, password=password)
    if user is not None:
        cache.delete(rate_key)
        login(request, user)
        _, raw_token = ApiToken.crear_para_usuario(user, nombre=device_name)
        return JsonResponse({
            'success': True,
            'token': raw_token,
            'user': {
                'username': user.username,
                'email': user.email
            }
        })

    cache.set(rate_key, attempts + 1, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    return JsonResponse({'success': False, 'error': 'Credenciales incorrectas'}, status=401)


@api_login_required
def api_logout(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    if getattr(request, 'api_token', None):
        ApiToken.objects.filter(pk=request.api_token.pk).update(activo=False)
    logout(request)
    return JsonResponse({'success': True})


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
    if pk is not None:
        producto = Producto.objects.filter(pk=pk).first()
        if not producto:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise TypeError
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    codigo_provisto = 'codigo_barras' in data
    codigo = str(data.get('codigo_barras') or '').strip() or None
    if codigo:
        exists_query = Producto.objects.filter(codigo_barras=codigo)
        if producto:
            exists_query = exists_query.exclude(pk=producto.pk)
        if exists_query.exists():
            return JsonResponse({'error': 'Ya existe un producto con este código de barras'}, status=400)

    nombre_raw = data.get('nombre')
    nombre = str(nombre_raw).strip() if nombre_raw is not None else None
    precio_costo_raw = data.get('precio_costo')
    precio_venta_raw = data.get('precio_venta')
    stock_actual_raw = data.get('stock_actual')
    stock_minimo_raw = data.get('stock_minimo', 5 if not producto else None)
    activo_en_catalogo = data.get('activo_en_catalogo', True if not producto else None)

    if not producto and not nombre:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
    if producto and nombre_raw is not None and not nombre:
        return JsonResponse({'error': 'El nombre no puede quedar vacío'}, status=400)

    try:
        precio_costo = (
            Decimal(str(precio_costo_raw)).quantize(CENT)
            if precio_costo_raw is not None
            else (None if producto else Decimal('0.00'))
        )
        precio_venta = (
            Decimal(str(precio_venta_raw)).quantize(CENT)
            if precio_venta_raw is not None
            else (None if producto else Decimal('0.00'))
        )
        stock_actual = (
            int(stock_actual_raw)
            if stock_actual_raw is not None
            else (None if producto else 0)
        )
        stock_minimo = (
            int(stock_minimo_raw)
            if stock_minimo_raw is not None
            else None
        )
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'error': 'Revisá los valores numéricos del producto'}, status=400)

    if (precio_costo is not None and precio_costo < 0) or (precio_venta is not None and precio_venta < 0):
        return JsonResponse({'error': 'Los precios no pueden ser negativos'}, status=400)
    if (stock_actual is not None and stock_actual < 0) or (stock_minimo is not None and stock_minimo < 0):
        return JsonResponse({'error': 'El stock no puede ser negativo'}, status=400)

    try:
        if producto:
            if nombre is not None:
                producto.nombre = nombre
            if codigo_provisto:
                producto.codigo_barras = codigo
            if precio_costo is not None:
                producto.precio_costo = precio_costo
            if precio_venta is not None:
                producto.precio_venta = precio_venta
            if stock_actual is not None:
                producto.stock_actual = stock_actual
            if stock_minimo is not None:
                producto.stock_minimo = stock_minimo
            if activo_en_catalogo is not None:
                producto.activo_en_catalogo = bool(activo_en_catalogo)
            producto.save()
        else:
            producto = Producto.objects.create(
                nombre=nombre,
                codigo_barras=codigo,
                precio_costo=precio_costo,
                precio_venta=precio_venta,
                stock_actual=stock_actual,
                stock_minimo=stock_minimo if stock_minimo is not None else 5,
                activo_en_catalogo=bool(activo_en_catalogo),
            )
    except IntegrityError:
        return JsonResponse({'error': 'Ya existe un producto con ese código de barras'}, status=409)
    except Exception:
        logger.exception('Error inesperado al guardar producto vía API')
        return JsonResponse({'error': 'No se pudo guardar el producto'}, status=500)

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

    producto = Producto.objects.filter(pk=pk).first()
    if not producto:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
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
    return JsonResponse([_cliente_data(cliente) for cliente in Cliente.objects.con_saldo()], safe=False)


@api_login_required
def api_cliente_guardar(request, pk=None):
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise TypeError
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nombre = str(data.get('nombre', '')).strip()
    if not nombre:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)

    if pk is not None:
        cliente = Cliente.objects.filter(pk=pk).first()
        if not cliente:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    else:
        cliente = Cliente()
    cliente.nombre = nombre
    cliente.telefono = str(data.get('telefono', '')).strip()
    if 'notas' in data:
        cliente.notas = str(data.get('notas') or '').strip()
    cliente.save()
    return JsonResponse(_cliente_data(cliente), status=200 if pk else 201)


@api_login_required
def api_cliente_movimientos(request, pk):
    cliente = Cliente.objects.filter(pk=pk).first()
    if not cliente:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

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
        if not isinstance(data, dict):
            raise TypeError
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    operacion_id = None
    operacion_id_raw = data.get('operacion_id')
    if operacion_id_raw:
        try:
            operacion_id = UUID(str(operacion_id_raw))
        except (TypeError, ValueError, AttributeError):
            return JsonResponse({'error': 'Identificador de operación inválido'}, status=400)

    try:
        fecha_operacion = date.fromisoformat(str(data.get('fecha')))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'La fecha debe usar el formato AAAA-MM-DD'}, status=400)

    try:
        monto_declarado = Decimal(str(data.get('monto_total'))).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'error': 'Monto total inválido'}, status=400)

    try:
        venta, creada, duplicada = registrar_venta_transaccional(
            fecha_operacion=fecha_operacion,
            metodo_pago=data.get('metodo_pago'),
            items_raw=data.get('items', []),
            notas=data.get('notas') or '',
            cliente_id=data.get('cliente_id'),
            operacion_id=operacion_id,
            monto_declarado=monto_declarado,
        )
        return _venta_response(venta, creada=creada, duplicada=duplicada)
    except VentaError as exc:
        return JsonResponse(exc.payload, status=exc.status_code)
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
