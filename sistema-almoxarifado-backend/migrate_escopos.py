# Arquivo: migrate_escopos.py
# Execute UMA vez para adicionar a coluna nova ao banco existente:
#   python migrate_escopos.py

import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./almoxarifado.db") \
            .replace("sqlite:///", "")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Verifica se a coluna já existe antes de tentar adicionar
cursor.execute("PRAGMA table_info(usuarios)")
colunas = [row[1] for row in cursor.fetchall()]

if "escopos_override" not in colunas:
    cursor.execute(
        "ALTER TABLE usuarios ADD COLUMN escopos_override TEXT DEFAULT NULL"
    )
    conn.commit()
    print("✓ Coluna 'escopos_override' adicionada com sucesso.")
else:
    print("✓ Coluna 'escopos_override' já existe — nada a fazer.")

conn.close()