from django.contrib import admin
from django.utils.html import format_html

from .models import Cliente, CuentaCorriente, Producto, VentaDiaria, VentaItem


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_venta', 'stock_actual', 'stock_minimo', 'estado_stock', 'activo_en_catalogo')
    list_editable = ('precio_venta', 'stock_actual', 'activo_en_catalogo')
    search_fields = ('nombre', 'codigo_barras')
    list_filter = ('activo_en_catalogo',)
    ordering = ('nombre',)

    @admin.display(description='stock')
    def estado_stock(self, obj):
        if obj.bajo_stock:
            return format_html('<strong style="color:#b42318;">Bajo</strong>')
        return format_html('<span style="color:#067647;">OK</span>')


class CuentaCorrienteInline(admin.TabularInline):
    model = CuentaCorriente
    extra = 1
    fields = ('tipo_movimiento', 'monto', 'descripcion', 'fecha')
    readonly_fields = ('fecha',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'saldo_total_admin')
    search_fields = ('nombre', 'telefono')
    inlines = (CuentaCorrienteInline,)

    @admin.display(description='saldo total')
    def saldo_total_admin(self, obj):
        saldo = obj.saldo_total()
        color = '#b42318' if saldo > 0 else '#067647'
        return format_html('<strong style="color:{};">${}</strong>', color, saldo)


@admin.register(CuentaCorriente)
class CuentaCorrienteAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'fecha', 'tipo_movimiento', 'monto', 'descripcion')
    list_filter = ('fecha', 'tipo_movimiento')
    search_fields = ('cliente__nombre', 'descripcion')
    autocomplete_fields = ('cliente',)
    date_hierarchy = 'fecha'


@admin.register(VentaDiaria)
class VentaDiariaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'metodo_pago', 'cliente', 'monto_total', 'operacion_id', 'notas')
    list_filter = ('fecha', 'metodo_pago')
    search_fields = ('operacion_id', 'cliente__nombre', 'notas', 'items__nombre_producto')
    readonly_fields = ('operacion_id',)
    date_hierarchy = 'fecha'

    class VentaItemInline(admin.TabularInline):
        model = VentaItem
        extra = 0
        can_delete = False
        fields = ('producto', 'nombre_producto', 'cantidad', 'precio_unitario', 'subtotal')
        readonly_fields = fields

        def has_add_permission(self, request, obj=None):
            return False

    inlines = (VentaItemInline,)
