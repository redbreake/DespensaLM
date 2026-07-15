# Despensa LM para Android

Aplicación interna para registrar ventas, escanear códigos de barras, administrar inventario y gestionar cuentas corrientes de clientes.

## Ejecutar

1. Abrí esta carpeta con Android Studio.
2. Esperá a que Gradle sincronice las dependencias.
3. Elegí un dispositivo o emulador con Android 7.0 o posterior.
4. Ejecutá la configuración `app`.

La app utiliza `https://despensalm.pythonanywhere.com/` como servidor predeterminado. La URL puede modificarse desde la configuración de la pantalla de acceso.

## Compilar APK de prueba

```powershell
gradle :app:assembleDebug
```

El APK se genera en `app/build/outputs/apk/debug/app-debug.apk`.
