# Despliegue en PythonAnywhere

## 1. Clonar el proyecto

```bash
git clone https://github.com/redbreake/DespensaLM.git
cd DespensaLM
```

## 2. Crear entorno virtual

```bash
mkvirtualenv despensavenv --python=/usr/bin/python3.10
pip install -r requirements.txt
```

## 3. Configurar variables

En la pestaña **Web** de PythonAnywhere, definir variables de entorno o agregarlas al archivo WSGI:

```python
os.environ["DJANGO_SECRET_KEY"] = "cambiar-por-una-clave-segura"
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_ALLOWED_HOSTS"] = "despensalm.pythonanywhere.com"
os.environ["WHATSAPP_PHONE"] = "549..."
os.environ["DJANGO_SESSION_COOKIE_SECURE"] = "True"
os.environ["DJANGO_CSRF_COOKIE_SECURE"] = "True"
os.environ["DJANGO_SECURE_HSTS_SECONDS"] = "3600"
```

## 4. Base de datos y archivos estaticos

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

## 5. WSGI

Ejemplo para `/var/www/tu_usuario_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

path = "/home/tu_usuario/DespensaLM"
if path not in sys.path:
    sys.path.append(path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_SECRET_KEY"] = "cambiar-por-una-clave-segura"
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_ALLOWED_HOSTS"] = "despensalm.pythonanywhere.com"
os.environ["WHATSAPP_PHONE"] = "549..."
os.environ["DJANGO_SESSION_COOKIE_SECURE"] = "True"
os.environ["DJANGO_CSRF_COOKIE_SECURE"] = "True"
os.environ["DJANGO_SECURE_HSTS_SECONDS"] = "3600"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

En **Static files** configurar:

- URL: `/static/` -> directorio: `/home/tu_usuario/DespensaLM/staticfiles`
- URL: `/media/` -> directorio: `/home/tu_usuario/DespensaLM/media`

## 6. Forzar HTTPS

En la pestaña **Web** de PythonAnywhere:

1. abrir la aplicación `despensalm.pythonanywhere.com`;
2. activar la opción **Force HTTPS**;
3. pulsar **Reload**;
4. verificar que `http://despensalm.pythonanywhere.com/` redirige a `https://`.

La redirección se configura en PythonAnywhere, no con `SECURE_SSL_REDIRECT`, para
evitar bucles entre Django y el proxy de la plataforma.

## 7. Respaldo antes de desplegar

Con el entorno virtual activado:

```bash
cd /home/DespensaLM/DespensaLM
python manage.py backup_despensa
```

El comando crea una carpeta dentro de `backups/` con:

- copia consistente de `db.sqlite3`;
- `media.zip`;
- `manifest.json` con hashes SHA-256;
- resultado de `PRAGMA integrity_check`.

No continuar con la migración si el comando no termina con
`Respaldo creado y verificado`.

## 8. Actualización segura

```bash
cd /home/DespensaLM/DespensaLM
workon despensavenv
git pull --ff-only
pip install -r requirements.txt
python manage.py backup_despensa
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

Después, pulsar **Reload** en la pestaña Web.

Verificaciones:

```bash
python manage.py showmigrations despensa
python manage.py check --deploy
```

Comprobar manualmente:

- catálogo público;
- login;
- panel;
- sincronización Android;
- venta de prueba controlada;
- reintento de la misma operación sin duplicación.

## 9. Rollback

Antes de desplegar, guardar el commit actual:

```bash
git rev-parse HEAD
```

Si el despliegue falla:

1. detener nuevas cargas desde Android;
2. volver al commit anterior;
3. restaurar la base respaldada;
4. restaurar `media`;
5. pulsar **Reload**;
6. comprobar login, productos, clientes y ventas.

Ejemplo de restauración:

```bash
cp backups/AAAAMMDDTHHMMSSZ/db.sqlite3 db.sqlite3
rm -rf /tmp/despensa-media-restore
mkdir -p /tmp/despensa-media-restore
unzip backups/AAAAMMDDTHHMMSSZ/media.zip -d /tmp/despensa-media-restore
rsync -a --delete /tmp/despensa-media-restore/ media/
python manage.py check
```

La restauración debe hacerse únicamente con la aplicación sin escrituras en
curso.
