"""
Rutas de la app de administración de ContaVen.

Endpoints:
  GET   /api/admin/yo                    -> datos del administrador que entró
  GET   /api/admin/usuarios              -> lista todos los usuarios con su licencia
  PATCH /api/admin/usuarios/<id>         -> bloquea, desbloquea o extiende licencias
  DELETE /api/admin/usuarios/<id>        -> elimina una cuenta
  GET   /api/admin/resumen               -> cifras globales (usuarios, licencias, bloqueados)
"""

from flask import Blueprint, g, jsonify, request

import supabase

rutas_admin = Blueprint("admin", __name__, url_prefix="/api/admin")


# ------------------------------------------------------------
# Función de apoyo: revisar que quien llama sea administrador
# ------------------------------------------------------------
def exigir_administrador() -> tuple:
    """
    Revisa el token de la cabecera Authorization y confirma que el
    correo esté en la tabla de administradores de Supabase.
    Devuelve (respuesta_json, codigo_http). Si todo está bien, (None, None).
    """
    cabecera = request.headers.get("Authorization", "")
    token = cabecera.replace("Bearer ", "").strip()

    # Sin token no se puede pasar
    if not token:
        return jsonify({"error": "No has iniciado sesión."}), 401

    # Se valida el token
    datos_usuario = supabase.verificar_token(token)
    if not datos_usuario:
        return jsonify({"error": "Tu sesión expiró. Vuelve a iniciar sesión."}), 401

    # Se revisa si el correo está autorizado como administrador
    if not supabase.es_administrador(datos_usuario.get("correo")):
        return jsonify({
            "error": "No tienes permisos de administrador.",
            "autorizado": False,
        }), 403

    # Se guardan los datos para usarlos en el resto de la función
    g.admin_id = datos_usuario["id"]
    g.admin_correo = datos_usuario["correo"]
    return None, None


# ------------------------------------------------------------
# GET /api/admin/yo
# Comprueba si el correo que entró es administrador
# ------------------------------------------------------------
@rutas_admin.get("/yo")
def revisar_perfil_admin():
    """Si el correo está en la lista de administradores, deja entrar al panel."""
    cabecera = request.headers.get("Authorization", "")
    token = cabecera.replace("Bearer ", "").strip()

    if not token:
        return jsonify({"error": "No has iniciado sesión."}), 401

    # Se valida el token
    datos_usuario = supabase.verificar_token(token)
    if not datos_usuario:
        return jsonify({"error": "Tu sesión expiró. Vuelve a iniciar sesión."}), 401

    # Se revisa la lista de administradores
    if not supabase.es_administrador(datos_usuario.get("correo")):
        return jsonify({
            "error": "Este correo no está autorizado como administrador.",
            "autorizado": False,
            "correo": datos_usuario.get("correo"),
        }), 403

    return jsonify({
        "autorizado": True,
        "id": datos_usuario["id"],
        "correo": datos_usuario["correo"],
    })


# ------------------------------------------------------------
# GET /api/admin/usuarios
# Lista todos los usuarios registrados con los días de licencia
# ------------------------------------------------------------
@rutas_admin.get("/usuarios")
def listar_usuarios():
    """
    Devuelve la lista completa de usuarios de la app de usuarios.
    Acepta un filtro opcional: ?buscar=texto  o  ?estado=vencida|bloqueada|activa
    """
    error, codigo = exigir_administrador()
    if error:
        return error, codigo

    usuarios = supabase.listar_usuarios()

    # --- Filtro por texto (nombre o correo) ---
    buscar = (request.args.get("buscar") or "").strip().lower()
    if buscar:
        usuarios = [
            u for u in usuarios
            if buscar in u.get("nombre", "").lower() or buscar in u.get("correo", "").lower()
        ]

    # --- Filtro por estado de la licencia ---
    estado = (request.args.get("estado") or "").strip().lower()
    if estado == "vencida":
        usuarios = [u for u in usuarios if u["licencia_vencida"] and not u["bloqueado"]]
    elif estado == "bloqueada":
        usuarios = [u for u in usuarios if u["bloqueado"]]
    elif estado == "activa":
        usuarios = [u for u in usuarios if not u["licencia_vencida"] and not u["bloqueado"]]

    return jsonify({"usuarios": usuarios, "total": len(usuarios)})


# ------------------------------------------------------------
# PATCH /api/admin/usuarios/<id>
# Bloquea, desbloquea o extiende la licencia de un usuario
# ------------------------------------------------------------
@rutas_admin.patch("/usuarios/<id_usuario>")
def cambiar_licencia(id_usuario: str):
    """
    Actualiza el acceso de un usuario. Body esperado (ejemplo):
      {"bloqueado": true,  "motivo_bloqueo": "Paga la licencia"}
      {"bloqueado": false}
      {"dias_a_agregar": 30}
    """
    error, codigo = exigir_administrador()
    if error:
        return error, codigo

    datos = request.get_json(silent=True) or {}

    # Se valida que venga al menos algo que cambiar
    if "bloqueado" not in datos and "dias_a_agregar" not in datos and "motivo_bloqueo" not in datos:
        return jsonify({
            "error": "Debes indicar «bloqueado», «motivo_bloqueo» o «dias_a_agregar»."
        }), 400

    try:
        perfil = supabase.actualizar_usuario(id_usuario, datos, g.admin_id)
    except ValueError as error_actualizar:
        return jsonify({"error": str(error_actualizar)}), 400

    if not perfil:
        return jsonify({"error": "Ese usuario no existe."}), 404

    # Mensaje según lo que se haya hecho
    if datos.get("bloqueado") is True:
        mensaje = "Usuario bloqueado. Ya no puede entrar a la app."
    elif datos.get("bloqueado") is False:
        mensaje = "Usuario desbloqueado. Ya puede entrar a la app."
    elif datos.get("dias_a_agregar") is not None:
        mensaje = f"Se agregaron {int(datos['dias_a_agregar'])} días a su licencia."
    else:
        mensaje = "Usuario actualizado."

    return jsonify({"mensaje": mensaje, "usuario": perfil})


# ------------------------------------------------------------
# DELETE /api/admin/usuarios/<id>
# Elimina completamente una cuenta
# ------------------------------------------------------------
@rutas_admin.delete("/usuarios/<id_usuario>")
def borrar_usuario(id_usuario: str):
    """Borra el perfil y la cuenta de autenticación de un usuario."""
    error, codigo = exigir_administrador()
    if error:
        return error, codigo

    # No se deja que el admin se borre a sí mismo por accidente
    if id_usuario == g.admin_id:
        return jsonify({"error": "No puedes eliminar tu propia cuenta."}), 400

    supabase.eliminar_usuario(id_usuario)
    return jsonify({"mensaje": "Usuario eliminado."})


# ------------------------------------------------------------
# GET /api/admin/resumen
# Cifras globales para el encabezado del panel
# ------------------------------------------------------------
@rutas_admin.get("/resumen")
def resumen_general():
    """Muestra cuántos usuarios hay, cuántos están bloqueados y cuántos tienen licencia vencida."""
    error, codigo = exigir_administrador()
    if error:
        return error, codigo

    usuarios = supabase.listar_usuarios()

    activos = [u for u in usuarios if not u["bloqueado"] and not u["licencia_vencida"]]
    vencidas = [u for u in usuarios if u["licencia_vencida"] and not u["bloqueado"]]
    bloqueados = [u for u in usuarios if u["bloqueado"]]

    return jsonify({
        "total_usuarios": len(usuarios),
        "licencias_activas": len(activos),
        "licencias_vencidas": len(vencidas),
        "usuarios_bloqueados": len(bloqueados),
    })
