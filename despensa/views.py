from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from decimal import Decimal

from .forms import ClienteForm, CuentaCorrienteForm, ProductoForm, VentaDiariaForm
from .models import Cliente, CuentaCorriente, Producto, VentaDiaria


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
    return render(
        request,
        'despensa/gestion/cliente_detalle.html',
        {
            'cliente': cliente,
            'form': form,
            'movimientos': cliente.movimientos.all(),
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
