# Despensa LM

Sistema Django para gestionar inventario, clientes, cuentas corrientes y un catalogo publico con pedidos por WhatsApp.

## Documentación

- [Auditoría web y hoja de ruta](docs/AUDITORIA_WEB_Y_HOJA_DE_RUTA.md)
- [Bloque 0: integridad y despliegue](docs/BLOQUE_0_INTEGRIDAD_Y_DESPLIEGUE.md)

## Desarrollo local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Variables utiles:

- `DJANGO_SECRET_KEY`: clave secreta para produccion.
- `DJANGO_DEBUG`: `True` o `False`.
- `DJANGO_ALLOWED_HOSTS`: hosts separados por coma.
- `WHATSAPP_PHONE`: numero internacional sin `+`, por ejemplo `549...`.

## Rutas

- `/`: catalogo publico.
- `/ingresar/`: login de gestion.
- `/gestion/`: panel propio para productos, clientes, fiados y caja.
- `/admin/`: gestion interna de productos, clientes, fiados y ventas diarias.
