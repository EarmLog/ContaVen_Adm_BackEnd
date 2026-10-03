"""
Prueba rápida del bloqueo de licencias de la app de ADMINISTRACIÓN.

Este archivo se usa con el backend de administración (ContaVen_Adm_BackEnd).

Para usarlo:
    1. Copia .env.ejemplo a .env y llénalo con las llaves de Supabase
    2. Registra un administrador con registrar_admin.py
    3. Arranca el backend de admin
    4. python prueba_admin.py
"""

import sys
import time
from pathlib import Path

import requests

# Se agrega la carpeta actual para poder importar los módulos del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent))

from configuracion import config

# Las llaves se leen del archivo ".env" para no dejarlas escritas en el código.
# La secret key nunca se sube a GitHub: el ".env" está en el .gitignore.
SUPABASE = config.SUPABASE_URL
LLAVE = config.SUPABASE_PUBLISHABLE_KEY
SECRETA = config.SUPABASE_SECRET_KEY
API = f"http://127.0.0.1:{config.PUERTO}"

# Se revisa que estén todas antes de pedir datos por consola
FALTAN = [
    nombre
    for nombre, valor in (
        ("SUPABASE_URL", SUPABASE),
        ("SUPABASE_PUBLISHABLE_KEY", LLAVE),
        ("SUPABASE_SECRET_KEY", SECRETA),
    )
    if not valor
]

if FALTAN:
    raise SystemExit(
        "Faltan datos en el archivo .env:\n  - "
        + "\n  - ".join(FALTAN)
        + "\n\nCopia .env.ejemplo a .env y llénalo con las llaves de tu proyecto de Supabase."
    )

# Correo del administrador que se registró antes
CORREO_ADMIN = input("Correo del administrador: ").strip()
CONTRASENA_ADMIN = input("Contraseña del administrador: ").strip()


def iniciar_sesion_admin() -> str:
    """Inicia sesión en Supabase con el correo del administrador."""
    print("\n=== LOGIN DEL ADMIN ===")

    respuesta = requests.post(
        f"{SUPABASE}/auth/v1/token?grant_type=password",
        headers={"apikey": LLAVE, "Content-Type": "application/json"},
        json={"email": CORREO_ADMIN, "password": CONTRASENA_ADMIN},
    )

    if respuesta.status_code != 200:
        raise SystemExit("No se pudo iniciar sesión como administrador.")

    token = respuesta.json()["access_token"]
    print("  Sesión iniciada correctamente.")
    return token


def comprobar_que_no_es_admin() -> None:
    """Revisa que un usuario normal NO pueda entrar a la app de administración."""
    print("\n=== UN USUARIO NORMAL NO PUEDE ENTRAR ===")

    # Se crea un usuario de prueba con su perfil y licencia
    correo = f"solve{int(time.time())}@contaven.com"
    respuesta = requests.post(
        f"{SUPABASE}/auth/v1/admin/users",
        headers={"apikey": SECRETA, "Authorization": f"Bearer {SECRETA}", "Content-Type": "application/json"},
        json={"email": correo, "password": "Prueba12345", "email_confirm": True},
    )
    usuario_id = respuesta.json()["id"]

    requests.post(
        f"{SUPABASE}/rest/v1/perfiles",
        headers={
            "apikey": SECRETA,
            "Authorization": f"Bearer {SECRETA}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={
            "id": usuario_id, "nombre": "Solo Usuario", "correo": correo,
            "telefono": None, "numero_carpeta_drive": 999, "dias_licencia": 30,
        },
    )

    # Se inicia sesión con ese usuario
    token_usuario = requests.post(
        f"{SUPABASE}/auth/v1/token?grant_type=password",
        headers={"apikey": LLAVE, "Content-Type": "application/json"},
        json={"email": correo, "password": "Prueba12345"},
    ).json()["access_token"]

    # Se intenta usar la API de administración
    estado = requests.get(
        f"{API}/api/admin/yo",
        headers={"Authorization": f"Bearer {token_usuario}"},
    ).status_code
    print(f"  Usuario normal en /api/admin/yo -> {estado} (debe ser 403)")

    lista = requests.get(
        f"{API}/api/admin/usuarios",
        headers={"Authorization": f"Bearer {token_usuario}"},
    ).status_code
    print(f"  Usuario normal en /api/admin/usuarios -> {lista} (debe ser 403)")

    # Se limpia el usuario de prueba
    requests.delete(
        f"{SUPABASE}/auth/v1/admin/users/{usuario_id}",
        headers={"apikey": SECRETA, "Authorization": f"Bearer {SECRETA}"},
    )


def probar_panel(token_admin: str) -> None:
    """Prueba el listado de usuarios, el bloqueo y el desbloqueo."""
    cab = {"Authorization": f"Bearer {token_admin}", "Content-Type": "application/json"}

    # --- Verificación de administrador ---
    print("\n=== VERIFICACIÓN DE ADMIN ===")
    yo = requests.get(f"{API}/api/admin/yo", headers=cab)
    print(f"  /api/admin/yo -> {yo.status_code}: {yo.json()}")

    # --- Listado de usuarios ---
    print("\n=== LISTA DE USUARIOS ===")
    usuarios = requests.get(f"{API}/api/admin/usuarios", headers=cab).json()["usuarios"]
    print(f"  Total de usuarios: {len(usuarios)}")

    for usuario in usuarios[:3]:
        print(f"    - {usuario['nombre']} ({usuario['correo']}) -> {usuario['dias_restantes']} días"
              f" | vencida: {usuario['licencia_vencida']} | bloqueado: {usuario['bloqueado']}")

    if not usuarios:
        print("  No hay usuarios todavía.")
        return

    objetivo = usuarios[0]
    print(f"\n  Usuario de prueba: {objetivo['correo']}")

    # --- Bloquear ---
    print("\n=== BLOQUEAR ===")
    respuesta = requests.patch(
        f"{API}/api/admin/usuarios/{objetivo['id']}",
        headers=cab,
        json={"bloqueado": True, "motivo_bloqueo": "Licencia vencida, paga para continuar."},
    )
    print(f"  Bloqueado -> {respuesta.status_code}: {respuesta.json()}")

    # Se revisa que el usuario ya no pueda usar la app de usuario
    token_usuario = requests.post(
        f"{SUPABASE}/auth/v1/token?grant_type=password",
        headers={"apikey": LLAVE, "Content-Type": "application/json"},
        json={"email": objetivo["correo"], "password": "Prueba12345"},
    )

    if token_usuario.status_code == 200:
        token = token_usuario.json()["access_token"]
        respuesta = requests.get(
            f"http://127.0.0.1:5001/api/auth/yo",
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"  App de usuario -> {respuesta.status_code}: {respuesta.json().get('error')}")

    # --- Desbloquear ---
    print("\n=== DESBLOQUEAR ===")
    respuesta = requests.patch(
        f"{API}/api/admin/usuarios/{objetivo['id']}",
        headers=cab,
        json={"bloqueado": False, "motivo_bloqueo": None},
    )
    print(f"  Desbloqueado -> {respuesta.status_code}: {respuesta.json().get('usuario', {}).get('bloqueado')}")

    # --- Extender licencia ---
    print("\n=== EXTENDER LICENCIA ===")
    respuesta = requests.patch(
        f"{API}/api/admin/usuarios/{objetivo['id']}",
        headers=cab,
        json={"dias_a_agregar": 30},
    )
    datos = respuesta.json().get("usuario", {})
    print(f"  +30 días -> {respuesta.status_code}: {datos.get('dias_restantes')} días restantes")

    # --- Resumen general ---
    print("\n=== RESUMEN GENERAL ===")
    resumen = requests.get(f"{API}/api/admin/resumen", headers=cab).json()
    print(f"  {resumen}")


if __name__ == "__main__":
    # Se espera a que el backend de admin arranque
    print("Esperando que el backend de administración arranque...")
    for _ in range(40):
        try:
            if requests.get(f"{API}/api/salud", timeout=2).status_code == 200:
                print("Backend listo.\n")
                break
        except requests.RequestException:
            time.sleep(0.5)

    token = iniciar_sesion_admin()
    comprobar_que_no_es_admin()
    probar_panel(token)
    print("\n=== PRUEBAS DE ADMIN COMPLETADAS ===")
