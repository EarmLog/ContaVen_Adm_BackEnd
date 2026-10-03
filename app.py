"""
ContaVen - Backend de la app de ADMINISTRACIÓN (Flask).

Este servidor maneja el panel de control global:
  - Lista de todos los usuarios registrados en la app de usuarios
  - Días de licencia que le quedan a cada uno
  - Bloquear o desbloquear el acceso de un usuario
  - Extender la licencia agregando días

Se conecta al mismo Supabase que la app de usuarios.

Para arrancarlo:
    pip install -r requirements.txt
    python app.py
"""

from flask import Flask, jsonify
from flask_cors import CORS

from configuracion import config
from rutas_admin import rutas_admin


def crear_aplicacion() -> Flask:
    """Crea y configura la aplicación Flask del panel de administración."""
    app = Flask(__name__)

    # Se permite que el frontend React (distinto puerto) llame a la API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Se registra el grupo de rutas del administrador
    app.register_blueprint(rutas_admin)

    # Ruta rápida para comprobar que el servidor está vivo
    @app.get("/api/salud")
    def salud():
        """Comprueba que el backend responde bien."""
        return jsonify({"mensaje": "ContaVen Adm API está funcionando."})

    return app


# Se crea la aplicación al importar este archivo
app = crear_aplicacion()


if __name__ == "__main__":
    # Arranca el servidor en el puerto indicado en el .env
    app.run(host="0.0.0.0", port=config.PUERTO, debug=True)
