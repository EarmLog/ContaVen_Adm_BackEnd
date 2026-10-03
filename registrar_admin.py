"""
Script para registrar al administrador de ContaVen.

Este script se usa UNA sola vez (o cada vez que quieras agregar
otro administrador). Corre con:

    python registrar_admin.py

Luego te va a pedir el correo y el nombre, y lo guarda en la tabla
"administradores" de Supabase.
"""

import sys
from pathlib import Path

# Se agrega la carpeta actual para poder importar los módulos del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent))

import supabase


def registrar() -> None:
    """
    Pide el correo y el nombre del administrador por consola
    y lo guarda en Supabase.
    """
    print("=== Registrar administrador de ContaVen ===\n")

    correo = input("Correo del administrador: ").strip().lower()
    nombre = input("Nombre (opcional): ").strip()

    # --- Validaciones ---
    if not correo:
        print("El correo es obligatorio.")
        return

    if "@" not in correo or "." not in correo.split("@")[-1]:
        print("Ese correo no tiene un formato válido.")
        return

    if " " in correo:
        print("El correo no puede tener espacios.")
        return

    try:
        # Se guarda el administrador en Supabase
        administrador = supabase.registrar_administrador(correo, nombre)
    except ValueError as error:
        print(f"No se pudo registrar: {error}")
        return

    print(f"\n¡Listo! {administrador['correo']} ya es administrador de ContaVen.")
    print("Ahora puede crear su cuenta en la app de administración con ese correo.")


def ver_lista() -> None:
    """Muestra la lista actual de administradores registrados."""
    print("\n=== Administradores registrados ===\n")

    administradores = supabase.listar_administradores()

    if not administradores:
        print("Todavía no hay ninguno.")
        return

    for administrador in administradores:
        estado = "activo" if administrador["activo"] else "desactivado"
        print(f"  - {administrador['correo']} ({estado})")


if __name__ == "__main__":
    print("1) Registrar un administrador nuevo")
    print("2) Ver la lista de administradores\n")

    opcion = input("Elige 1 o 2: ").strip()

    if opcion == "1":
        registrar()
    elif opcion == "2":
        ver_lista()
    else:
        print("Opción no válida.")
