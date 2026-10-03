# ContaVen — Backend de administración

API en Flask del panel de administración de ContaVen. Sirve para ver a todos los usuarios registrados y manejar sus licencias.

## Qué hace

Desde el panel, el administrador de ContaVen puede:

- Ver la lista completa de usuarios con sus datos y los días de licencia que les quedan.
- Bloquear o desbloquear el acceso a la app de usuarios.
- Agregar días de licencia.
- Eliminar una cuenta.
- Ver cifras globales: total de usuarios, licencias activas, vencidas y bloqueados.

Es un proyecto corto a propósito. Toda la escritura se hace contra Supabase, que es la misma base que usa la app de usuarios.

## Cómo está armado

- **Flask 3** con un solo blueprint (`rutas_admin`).
- **Supabase** como fuente de los perfiles. Este backend usa la llave secreta, que nunca sale del servidor.
- La tabla **`administradores`** de Supabase guarda los correos autorizados. Antes de ejecutar cualquier ruta se valida el token y se comprueba que el correo esté ahí y activo.

## Requisitos

- Python 3.10 o superior
- Acceso al mismo proyecto de Supabase que usa la app de usuarios

## Instalación

```bash
cd ContaVen_Adm_BackEnd
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.ejemplo .env
```

Completa `SUPABASE_SECRET_KEY` en el `.env`.

## Variables de entorno

| Variable | Para qué |
| --- | --- |
| `PUERTO` | Puerto del servidor (por defecto 5002) |
| `SUPABASE_URL` | Dirección del proyecto de Supabase |
| `SUPABASE_SECRET_KEY` | Llave secreta; se usa solo en el servidor |
| `SUPABASE_PUBLISHABLE_KEY` | Llave pública |
| `SUPABASE_JWKS_URL` | Llaves públicas para validar los tokens |

## Registrar un administrador

Antes de entrar al panel, el correo tiene que estar en la tabla `administradores`. Hay un script para eso:

```bash
.venv/bin/python registrar_admin.py
```

Pide el correo y un nombre. Después, esa persona crea su cuenta en la app de administración con ese mismo correo y contraseña.

## Cómo arrancarlo

```bash
.venv/bin/python app.py
```

Queda en `http://localhost:5002`. Comprobación rápida:

```bash
curl http://localhost:5002/api/salud
```

## Endpoints

Todos piden `Authorization: Bearer <token>` de un administrador autorizado.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/api/admin/yo` | Comprueba que el correo es administrador |
| GET | `/api/admin/usuarios` | Lista los usuarios; acepta `?buscar=` y `?estado=` |
| PATCH | `/api/admin/usuarios/<id>` | Bloquea, desbloquea o agrega días |
| DELETE | `/api/admin/usuarios/<id>` | Elimina la cuenta |
| GET | `/api/admin/resumen` | Cifras globales |
| GET | `/api/salud` | Comprueba que el servidor responde |

El `?estado=` acepta `activa`, `vencida` y `bloqueada`.

Ejemplos de cuerpo para el `PATCH`:

```json
{ "bloqueado": true, "motivo_bloqueo": "Paga la licencia para entrar." }
{ "bloqueado": false }
{ "dias_a_agregar": 30 }
```

## Estructura

```
ContaVen_Adm_BackEnd/
├── app.py              # crea la app y registra las rutas
├── configuracion.py    # lee el .env
├── rutas_admin.py      # endpoints y validación del administrador
├── supabase.py         # llamadas a Supabase
├── registrar_admin.py  # script para dar de alta administradores
├── prueba_admin.py     # prueba del panel
└── requirements.txt
```

## Prueba

```bash
.venv/bin/python prueba_admin.py
```

Pide el correo y la contraseña de un administrador y recorre las operaciones principales.

## Notas

- El backend no deja que un administrador elimine su propia cuenta.
- Si cambias de proyecto de Supabase, actualiza las cuatro variables en el `.env`.
- Aquí no se guardan datos del negocio: solo se leen y modifican perfiles.
