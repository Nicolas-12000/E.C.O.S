import os

# Debe estar antes de importar app.main (Settings lee el env al cargar).
os.environ["CHAT_DEMO_AUTH_REQUIRED"] = "false"
