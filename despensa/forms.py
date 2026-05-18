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
            'descripcion': forms.TextInput(attrs={'placeholder': 'Opcional (Por defecto: Mercaderías varias)'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        descripcion = cleaned_data.get('descripcion', '').strip()
        tipo_movimiento = cleaned_data.get('tipo_movimiento')
        
        if not descripcion and tipo_movimiento:
            if tipo_movimiento == 'DEUDA':
                cleaned_data['descripcion'] = 'Mercaderías varias'
            elif tipo_movimiento == 'PAGO':
                cleaned_data['descripcion'] = 'Entrega de dinero'
                
        return cleaned_data


class VentaDiariaForm(forms.ModelForm):
    class Meta:
        model = VentaDiaria
        fields = ('monto_total', 'metodo_pago', 'notas')
        widgets = {
            'monto_total': forms.NumberInput(attrs={'step': '0.01'}),
            'notas': forms.TextInput(attrs={'placeholder': 'Opcional (Por defecto: Mercaderías varias)'}),
        }

    def clean_notas(self):
        notas = self.cleaned_data.get('notas', '').strip()
        if not notas:
            return 'Mercaderías varias'
        return notas
