from django import forms

from .models import Cliente, CuentaCorriente, Producto, VentaDiaria


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = (
            'codigo_barras',
            'nombre',
            'precio_costo',
            'precio_venta',
            'stock_actual',
            'stock_minimo',
            'activo_en_catalogo',
            'imagen',
        )
        widgets = {
            'codigo_barras': forms.TextInput(attrs={'placeholder': 'Opcional'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Yerba, azucar, leche'}),
            'precio_costo': forms.NumberInput(attrs={'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'step': '0.01'}),
            'stock_actual': forms.NumberInput(attrs={'min': '0'}),
            'stock_minimo': forms.NumberInput(attrs={'min': '0'}),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ('nombre', 'telefono', 'notas')
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del cliente'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Telefono o WhatsApp'}),
            'notas': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Direccion, referencia o comentario'}),
        }


class CuentaCorrienteForm(forms.ModelForm):
    class Meta:
        model = CuentaCorriente
        fields = ('tipo_movimiento', 'monto', 'descripcion')
        widgets = {
            'monto': forms.NumberInput(attrs={'step': '0.01'}),
            'descripcion': forms.TextInput(attrs={'placeholder': 'Ej: Compra fiada o entrega a cuenta'}),
        }


class VentaDiariaForm(forms.ModelForm):
    class Meta:
        model = VentaDiaria
        fields = ('monto_total', 'metodo_pago', 'notas')
        widgets = {
            'monto_total': forms.NumberInput(attrs={'step': '0.01'}),
            'notas': forms.TextInput(attrs={'placeholder': 'Detalle opcional'}),
        }
