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
os.environ["DJANGO_ALLOWED_HOSTS"] = "tu_usuario.pythonanywhere.com"
os.environ["WHATSAPP_PHONE"] = "549..."
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
os.environ["DJANGO_ALLOWED_HOSTS"] = "tu_usuario.pythonanywhere.com"
os.environ["WHATSAPP_PHONE"] = "549..."

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

En **Static files** configurar:

- URL: `/static/` -> directorio: `/home/tu_usuario/DespensaLM/staticfiles`
- URL: `/media/` -> directorio: `/home/tu_usuario/DespensaLM/media`
