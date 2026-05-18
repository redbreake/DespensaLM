# Plan de Desarrollo Agentico: Sistema de Gestion y Catalogo - Despensa LM

Este documento resume el plan seguido para construir un MVP de **Despensa LM** con Django, orientado a despliegue simple en PythonAnywhere.

## Mejoras aplicadas al plan original

- Se corrigio el texto con caracteres rotos para dejar la documentacion legible.
- Se agregaron variables de entorno para `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y telefono de WhatsApp.
- Se incluyo una imagen opcional por producto para que el catalogo pueda mostrar fotos cuando existan.
- Se agregaron validaciones de montos y stock para evitar valores negativos.
- Se separo una guia de despliegue practica en `DESPLIEGUE_PYTHONANYWHERE.md`.

## Fase 1: Inicializacion y configuracion

- Proyecto Django con app `despensa`.
- Dependencias en `requirements.txt`: Django LTS 4.2 y Pillow.
- Configuracion local compatible con SQLite.
- Archivos estaticos y multimedia preparados para PythonAnywhere.
- Idioma `es-ar` y zona horaria `America/Argentina/Buenos_Aires`.

## Fase 2: Modelo de datos

- `Producto`: codigo de barras, nombre, precios, stock, stock minimo, estado en catalogo e imagen opcional.
- `Cliente`: datos basicos y saldo calculado desde sus movimientos.
- `CuentaCorriente`: deudas y pagos asociados a clientes.
- `VentaDiaria`: registro simple de caja por metodo de pago.

## Fase 3: Django Admin como gestion interna

- Busqueda y edicion rapida de productos.
- Indicador visual de bajo stock.
- Clientes con saldo total e inline de movimientos de cuenta corriente.
- Filtros y buscador para fiados, pagos y ventas.

## Fase 4: Catalogo publico y WhatsApp

- Vista publica en `/` con productos activos y con stock.
- Plantilla responsive para telefonos.
- Carrito local con `localStorage`.
- Envio del pedido por `https://wa.me/` usando `WHATSAPP_PHONE`.

## Fase 5: Despliegue

- Instrucciones paso a paso en `DESPLIEGUE_PYTHONANYWHERE.md`.
- Comandos de migracion, superusuario, `collectstatic` y ejemplo de WSGI.
