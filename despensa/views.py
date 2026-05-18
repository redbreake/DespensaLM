from django.conf import settings
from django.shortcuts import render

from .models import Producto


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
