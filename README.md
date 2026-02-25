# MailRouter 📨

Sistema automático de recepción y reenvío rotativo de correos con dashboard web.

## Estructura del proyecto

```
mailrouter/
├── app.py                  # Entry point — inicialización y registro de blueprints
├── config.py               # Carga/guardado de configuración en config.json
├── requirements.txt
├── README.md
│
├── models/
│   └── database.py         # Init DB, queries (get, insert, update)
│
├── services/
│   ├── mail_reader.py      # Conexión IMAP, lectura de correos no vistos
│   ├── mail_sender.py      # SMTP, construcción del reenvío, rotación
│   └── worker.py           # Thread de monitoreo en segundo plano
│
├── routes/
│   ├── dashboard.py        # Vistas principales y control del worker
│   ├── recipients.py       # CRUD de destinatarios
│   ├── config_routes.py    # Guardar configuración del servidor
│   └── api.py              # Endpoints REST /api/emails y /api/stats
│
├── templates/
│   ├── base.html           # Layout base (sidebar, flash, scripts)
│   ├── dashboard.html      # Dashboard principal
│   └── email_detail.html   # Vista de detalle de un correo
│
└── static/
    ├── css/
    │   └── main.css        # Estilos globales
    └── js/
        └── dashboard.js    # Flash dismiss + polling de stats
```

## Instalación y arranque

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Configuración de Gmail

1. Activa IMAP: Gmail → Configuración → Reenvío e IMAP
2. Crea una App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Rellena email + App Password en el dashboard → Guardar

## Cómo funciona la rotación

Cada correo entrante se asigna al siguiente destinatario activo de la lista.
Al llegar al final vuelve al primero. El badge **NEXT** en el dashboard
muestra quién recibirá el próximo correo.

## Producción

```bash
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 "app:app"
```

> Usa `-w 1` (un solo worker) para evitar que el thread de monitoreo se duplique.

## API REST

| Método | Ruta        | Descripción                      |
| ------ | ----------- | -------------------------------- |
| GET    | /api/emails | Lista paginada de correos        |
| GET    | /api/stats  | Estadísticas + estado del worker |
