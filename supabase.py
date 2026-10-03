"""
Funciones para hablar con Supabase desde la app de administración.

El backend de admin usa la llave secreta para poder:
  - Ver todos los usuarios registrados (el usuario normal solo ve el suyo)
  - Cambiar los días de licencia
  - Bloquear o desbloquear el acceso a la app de usuarios
"""

import requests
from jwt import PyJWKClient

from configuracion import config

# Cliente que descarga las llaves públicas de Supabase para validar los tokens
_cliente_jwks = PyJWKClient(config.SUPABASE_JWKS_URL)


def _cabeceras() -> dict:
    """
    Arma las cabeceras HTTP con la llave secreta de Supabase.
    Esa llave nunca se manda al navegador, solo se usa aquí en el backend.
    """
    return {
        "apikey": config.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def verificar_token(token: str) -> dict | None:
    """
    Valida el token de sesión del administrador.
    Devuelve sus datos (id y correo) o None si el token no es válido.
    """
    import jwt

    try:
        llave = _cliente_jwks.get_signing_key_from_jwt(token)
        datos = jwt.decode(
            token,
            llave.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_aud": False},
        )
        return {"id": datos.get("sub"), "correo": datos.get("email")}
    except Exception:
        return None


def es_administrador(correo: str) -> bool:
    """
    Revisa si un correo está en la tabla de administradores de Supabase
    y además está activo. Si está en la lista, puede entrar al panel.
    """
    if not correo:
        return False

    respuesta = requests.get(
        f"{config.SUPABASE_URL}/rest/v1/administradores",
        headers=_cabeceras(),
        params={"correo": f"eq.{correo}", "activo": "eq.true", "select": "id"},
        timeout=30,
    )

    if respuesta.status_code != 200:
        return False

    return len(respuesta.json()) > 0


def registrar_administrador(correo: str, nombre: str = "") -> dict:
    """
    Agrega un correo a la lista de administradores para que pueda
    entrar al panel de control de ContaVen.
    """
    respuesta = requests.post(
        f"{config.SUPABASE_URL}/rest/v1/administradores",
        headers={**_cabeceras(), "Prefer": "return=representation"},
        json={"correo": correo, "nombre": nombre or correo},
        params={"select": "*"},
        timeout=30,
    )

    if respuesta.status_code not in (200, 201):
        raise ValueError(f"No se pudo registrar el administrador: {respuesta.text}")

    return respuesta.json()[0]


def listar_administradores() -> list:
    """Devuelve la lista de correos autorizados a usar la app de admin."""
    respuesta = requests.get(
        f"{config.SUPABASE_URL}/rest/v1/administradores",
        headers=_cabeceras(),
        params={"select": "*", "order": "creado_en.asc"},
        timeout=30,
    )

    return respuesta.json() if respuesta.status_code == 200 else []


def listar_usuarios() -> list:
    """
    Trae todos los perfiles registrados en la app de usuarios con
    los datos de su licencia, más la fecha en que-create la cuenta.
    """
    # Se piden los perfiles ordenados del más nuevo al más viejo
    respuesta = requests.get(
        f"{config.SUPABASE_URL}/rest/v1/perfiles",
        headers=_cabeceras(),
        params={"select": "*", "order": "creado_en.desc"},
        timeout=30,
    )

    if respuesta.status_code != 200:
        return []

    perfiles = respuesta.json()

    # A cada perfil se le calculan los días que le quedan
    for perfil in perfiles:
        perfil["dias_restantes"] = calcular_dias_restantes(perfil.get("fecha_fin_licencia"))
        perfil["licencia_vencida"] = perfil["dias_restantes"] <= 0

    return perfiles


def actualizar_usuario(usuario_id: str, datos: dict, admin_id: str | None = None) -> dict | None:
    """
    Cambia los datos de licencia de un usuario.
    Acepta estos campos:
      bloqueado          -> True para dejarle entrar, False para bloquearle
      motivo_bloqueo     -> texto explicando por qué se le bloqueó
      dias_a_agregar     -> días que se le suman a su licencia
      fecha_fin_licencia -> si se quiere poner una fecha fija
    """
    # Se arma solo con los campos que se quieren cambiar
    cambios = {}

    if "bloqueado" in datos:
        cambios["bloqueado"] = bool(datos["bloqueado"])

    if "motivo_bloqueo" in datos:
        cambios["motivo_bloqueo"] = datos["motivo_bloqueo"]

    if datos.get("bloqueado"):
        cambios["bloqueado_por"] = admin_id
        cambios["bloqueado_en"] = None  # Supabase lo pone con now() si se manda "now"

    # Si se mandan días a agregar, se recalcula la fecha de vencimiento
    dias = datos.get("dias_a_agregar")
    if dias is not None:
        try:
            dias = int(dias)
            # Se busca la fecha de fin actual del usuario para sumarle
            perfil = requests.get(
                f"{config.SUPABASE_URL}/rest/v1/perfiles",
                headers=_cabeceras(),
                params={"id": f"eq.{usuario_id}", "select": "fecha_fin_licencia,dias_licencia"},
                timeout=30,
            ).json()

            if perfil:
                fecha_actual = perfil[0]["fecha_fin_licencia"]
                # Si la licencia ya vencio se cuenta desde hoy
                dias_actuales = calcular_dias_restantes(fecha_actual)
                base = dias_actuales if dias_actuales > 0 else 0
                total = base + dias
                cambios["dias_licencia"] = total
                cambios["_nueva_fecha"] = total
        except (ValueError, TypeError):
            pass

    if not cambios:
        return None

    # Se separa el campo auxiliar de la fecha
    nueva_fecha = cambios.pop("_nueva_fecha", None)

    # Se manda la actualización a Supabase
    respuesta = requests.patch(
        f"{config.SUPABASE_URL}/rest/v1/perfiles",
        headers={**_cabeceras(), "Prefer": "return=representation"},
        params={"id": f"eq.{usuario_id}", "select": "*"},
        json=cambios,
        timeout=30,
    )

    if respuesta.status_code != 200:
        raise ValueError(f"No se pudo actualizar el usuario: {respuesta.text}")

    perfil = respuesta.json()[0]

    # Si se baskaron días, se fija la nueva fecha de vencimiento con SQL
    if nueva_fecha is not None:
        respuesta = requests.post(
            f"{config.SUPABASE_URL}/rest/v1/rpc/actualizar_dias_licencia",
            headers=_cabeceras(),
            json={"p_id": usuario_id, "p_dias": nueva_fecha},
            timeout=30,
        )
        # Se vuelve a leer el perfil con la fecha ya actualizada
        if respuesta.status_code == 200:
            perfil["fecha_fin_licencia"] = respuesta.json()

    perfil["dias_restantes"] = calcular_dias_restantes(perfil.get("fecha_fin_licencia"))
    perfil["licencia_vencida"] = perfil["dias_restantes"] <= 0

    return perfil


def eliminar_usuario(usuario_id: str) -> None:
    """
    Borra un usuario de la tabla de perfiles y de la autenticación.
    Solo se usa si el administrador quiere eliminar una cuenta.
    """
    # Primero se borra de los perfiles
    requests.delete(
        f"{config.SUPABASE_URL}/rest/v1/perfiles",
        headers=_cabeceras(),
        params={"id": f"eq.{usuario_id}"},
        timeout=30,
    )

    # Luego se borra de la autenticación de Supabase
    requests.delete(
        f"{config.SUPABASE_URL}/auth/v1/admin/users/{usuario_id}",
        headers=_cabeceras(),
        timeout=30,
    )


def calcular_dias_restantes(fecha_fin: str | None) -> int:
    """
    Cuenta los días que le quedan de licencia a un usuario.
    Si la fecha ya pasó devuelve 0. Nunca devuelve números negativos.
    """
    from datetime import datetime, timezone

    if not fecha_fin:
        return 0

    try:
        fin = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
        ahora = datetime.now(timezone.utc)
        diferencia = fin - ahora

        # Se convierte a días y se redondea hacia arriba
        dias = int(-(-diferencia.total_seconds() // 86400))
        return max(dias, 0)
    except Exception:
        return 0
