"""
Configuración general del backend de administración de ContaVen.

Lee las variables de entorno del archivo ".env" y las guarda en un
objeto "config" que usan el resto de archivos.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carpeta donde vive este archivo (el backend de admin)
CARPETA_BACKEND = Path(__file__).resolve().parent

# Carga el archivo .env si existe
load_dotenv(CARPETA_BACKEND / ".env")


class Config:
    """Valores de configuración leídos del archivo .env."""

    # --- Servidor ---
    PUERTO = int(os.getenv("PUERTO", 5002))

    # --- Supabase (mismo proyecto que la app de usuarios) ---
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_JWKS_URL = os.getenv(
        "SUPABASE_JWKS_URL",
        SUPABASE_URL + "/auth/v1/.well-known/jwks.json",
    )


# Objeto único de configuración que se importa en los demás archivos
config = Config()
