"""
(api/index.py)
Punto de entrada del backend de administración en Vercel.

Vercel detecta este archivo y lo convierte en una función serverless.
Solo expone la aplicación Flask que ya está en "app.py", así que el mismo
código sirve para desarrollo local y para producción.

Este backend es sin estado: no guarda nada en disco, todo vive en Supabase.
Eso es justo lo que hace que funcione bien en Vercel.
"""

from app import app

# Vercel busca una variable llamada "app" (Flask) o "handler" (WSGI) en este
# archivo. "app" cumple las dos cosas: Flask es un callable compatible WSGI.
__all__ = ["app"]