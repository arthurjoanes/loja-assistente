"Cria .env sem sobrescrever valores existentes."
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print(".env já existe.")
else:
    content = (root / ".env.example").read_text(encoding="utf-8")
    content = content.replace("replace-with-random-project-only-secret", secrets.token_hex(32))
    content = content.replace("local-demo-only-change-for-shared-environments", secrets.token_hex(24))
    if os.name == "posix":
        content = content.replace("LOCAL_UID=1000", f"LOCAL_UID={os.getuid()}")
        content = content.replace("LOCAL_GID=1000", f"LOCAL_GID={os.getgid()}")
    target.write_text(content, encoding="utf-8")
    print(".env criado.")
