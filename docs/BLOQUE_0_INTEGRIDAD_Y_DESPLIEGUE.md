# Bloque 0: integridad y despliegue

## Objetivo

Evitar que una venta se duplique, descuente stock parcialmente o pierda su fecha
y detalle al sincronizarse desde Android.

## Contrato de venta

Endpoint:

```text
POST /api/ventas/
```

Ejemplo:

```json
{
  "operacion_id": "8db86085-ae6d-4436-a035-56395ac68981",
  "fecha": "2026-07-20",
  "monto_total": 3000.0,
  "metodo_pago": "EFECTIVO",
  "notas": "Venta",
  "cliente_id": null,
  "items": [
    {
      "producto_id": 12,
      "cantidad": 2,
      "precio_unitario": 1500.0
    }
  ]
}
```

Reglas:

- `operacion_id` es un UUID generado una sola vez por Android;
- todos los reintentos de la misma venta usan el mismo UUID;
- el servidor agrupa productos repetidos;
- el servidor calcula cada subtotal y el total;
- el total enviado debe coincidir con los renglones nuevos;
- la venta se rechaza completa cuando no hay stock suficiente;
- venta, artículos, stock y fiado se guardan en una sola transacción;
- repetir un UUID devuelve la venta existente sin volver a descontar stock;
- `fecha` conserva el día original, incluso si la sincronización ocurre después.

Respuesta nueva:

```json
{
  "success": true,
  "venta_id": 42,
  "operacion_id": "8db86085-ae6d-4436-a035-56395ac68981",
  "monto_total": "3000.00",
  "duplicada": false
}
```

Una operación repetida responde `200` con `duplicada: true`. Una operación nueva
responde `201`.

## Compatibilidad con la APK anterior

El backend todavía admite solicitudes sin `operacion_id` y artículos sin
`precio_unitario`.

En ese modo:

- la venta no tiene garantía de idempotencia;
- el servidor usa el precio actual del producto;
- el total se calcula en el servidor;
- se conserva el soporte para ventas que ya estaban pendientes.

La migración Room `1 -> 2`:

- conserva todas las ventas locales;
- agrega `operation_id`;
- asigna un UUID determinista a filas antiguas;
- crea un índice único;
- reemplaza la migración destructiva anterior.

## Orden de despliegue

1. Bloquear temporalmente nuevas ventas desde Android.
2. Crear y verificar el respaldo de producción.
3. Desplegar backend y migración Django.
4. Validar login, catálogo, productos, clientes y API.
5. Activar `Force HTTPS` en PythonAnywhere.
6. Instalar la APK nueva.
7. Abrir la aplicación y permitir que Room migre la base local.
8. Sincronizar ventas pendientes.
9. Realizar una venta controlada.
10. Repetir la misma solicitud y confirmar que no cambia stock ni saldo.

El backend se despliega primero porque mantiene compatibilidad con la APK
anterior. La APK nueva no debe usarse contra el backend anterior: enviaría campos
que el código antiguo ignoraría y no existiría garantía de idempotencia.

## Respaldo

```bash
python manage.py backup_despensa
```

El resultado contiene:

- `db.sqlite3`;
- `media.zip`;
- `manifest.json`;
- hashes SHA-256;
- validación `PRAGMA integrity_check`.

## Verificación

Backend:

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py check
```

Android:

```text
:app:assembleDebug
:app:testDebugUnitTest --tests com.example.FlexibleDoubleAdapterTest
:app:testDebugUnitTest --tests com.example.SaleRequestSerializationTest
```

## Rollback

Si falla el backend antes de registrar ventas nuevas:

1. restaurar el commit anterior;
2. restaurar `db.sqlite3` y `media`;
3. recargar la aplicación web.

Si ya se registraron ventas con el modelo nuevo, no restaurar una base anterior
sin revisar primero esas operaciones: se perderían ventas posteriores al
respaldo.

Si falla la APK:

- no borrar sus datos;
- conservar las ventas pendientes;
- volver a la versión anterior solo después de confirmar que no quedan filas
  creadas con el esquema Room 2.
