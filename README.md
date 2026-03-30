# Mail Router

Mail Router es una aplicación web en Python/Flask que monitorea una bandeja de entrada IMAP, registra los correos entrantes en una base de datos SQLite y los reenvía automáticamente a destinatarios configurables mediante SMTP.

## Características

- Panel web de administración con autenticación (`Flask-Login`)
- Gestión de destinatarios: agregar, actualizar, activar/desactivar y eliminar
- Rotación automática de destinatarios para el reenvío de correos
- Worker en segundo plano que consulta la bandeja de entrada periódicamente
- Reenvío de correos pendientes, con detección de errores y estados
- API REST básica para estadísticas y listado de correos
- Gestión de usuarios con roles `admin` y `user`

## Requisitos

- Python 3.11+ (o compatible con las dependencias)
- `pip`
- Cuenta de correo con acceso IMAP y SMTP
- Dependencias listadas en `requirements.txt`

## Instalación

1. Clona el repositorio o descarga el proyecto.
2. Crea y activa un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instala las dependencias:

```powershell
pip install -r requirements.txt
```

4. Inicia la aplicación:

```powershell
python app.py
```

5. Abre el navegador en `http://127.0.0.1:5000`

## Configuración

La configuración principal se encuentra en `config.json`.

Valores clave:

- `imap_host`: servidor IMAP
- `imap_port`: puerto IMAP (normalmente `993` para SSL)
- `smtp_host`: servidor SMTP
- `smtp_port`: puerto SMTP (normalmente `587` para STARTTLS)
- `email_address`: email usado para conectarse a IMAP/SMTP
- `email_password`: contraseña del email
- `check_interval`: intervalo en segundos entre chequeos del worker
- `active`: habilita o deshabilita el worker automático

> Nota: `config.json` almacena credenciales, evita subirlo a repositorios públicos.

## Uso

- Inicia sesión en `/login`.
- El primer inicio crea automáticamente un usuario `admin` con contraseña `admin123` si no existe ningún usuario.
- En el dashboard puedes:
  - ver correos registrados
  - iniciar/detener el worker
  - forzar un chequeo inmediato
  - administrar destinatarios
  - actualizar configuración de correo
  - administrar usuarios (solo admin)

## Rutas importantes

- `/login` - formulario de acceso
- `/` - dashboard principal
- `/worker/start` - iniciar worker
- `/worker/stop` - detener worker
- `/worker/check-now` - procesar bandeja de entrada manualmente
- `/api/stats` - estadísticas JSON
- `/api/emails` - listado de correos paginado

## Estructura del proyecto

- `app.py` - punto de entrada principal
- `config.py` / `config.json` - carga y guarda la configuración
- `models/database.py` - base de datos SQLite y operaciones CRUD
- `models/user.py` - modelo de usuario para Flask-Login
- `routes/` - rutas de Flask organizadas por funcionalidad
- `services/` - lógica de lectura IMAP, envío SMTP y worker
- `templates/` - vistas HTML
- `static/` - scripts y recursos estáticos

## Base de datos

- Usa SQLite en `mailrouter.db`
- Tablas principales:
  - `emails`
  - `recipients`
  - `rotation_state`
  - `users`

## Advertencias

- Cambia la contraseña por defecto del admin después del primer inicio.
- Mantén `config.json` seguro y no lo subas con datos reales.
- El worker se ejecuta en un hilo separado con `use_reloader=False` para evitar reinicios duplicados.

## Prueba rápida

`test_forward.py` contiene un ejemplo de reenviar directamente un correo desde IMAP a SMTP sin pasar por Flask.

## Créditos

Desarrollado como una herramienta de enrutamiento y monitoreo de correo entrante con reenvío basado en destinatarios rotativos.
