# test_forward.py — test de reenvío directo sin pasar por Flask
import imaplib
import smtplib
import email
import copy
import config

# ── Cambia estos valores ──────────────────────────────
EMAIL    = config.DEFAULT_CONFIG['email_address']
PASSWORD = config.DEFAULT_CONFIG['email_password']
DESTINO  = "jefferson.vivas.95@outlook.es"
# ─────────────────────────────────────────────────────

# 1. Conectar y coger el último correo del inbox
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(EMAIL, PASSWORD)
mail.select("INBOX")

_, search_data = mail.search(None, "ALL")
uids = search_data[0].split()
last_uid = uids[-1]  # el más reciente

_, msg_data = mail.fetch(last_uid, "(RFC822)")
raw_bytes = msg_data[0][1]
msg = email.message_from_bytes(raw_bytes)
mail.logout()

print(f"Correo: {msg.get('Subject')}")
print(f"Partes MIME:")
for part in msg.walk():
    print(f"  {part.get_content_type()} | {part.get('Content-Disposition','—')}")

# 2. Reenviar el raw directamente sin tocar nada
fwd = copy.deepcopy(msg)

del fwd["From"]
del fwd["To"]
del fwd["Subject"]

fwd["From"]    = EMAIL
fwd["To"]      = DESTINO
fwd["Subject"] = f"TEST ADJUNTO DIRECTO"

# 3. Enviar
with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.sendmail(EMAIL, DESTINO, fwd.as_bytes())
    print("✓ Enviado")
