# Arquivo: migrate_numero_movimento.py
# Execute UMA vez para adicionar a coluna nova ao banco existente:
#   python migrate_numero_movimento.py

import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./almoxarifado.db") \
            .replace("sqlite:///", "")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Verifica se a tabela existe (caso o banco seja novo)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transferencias'")
if not cursor.fetchone():
    print("⚠️ A tabela 'transferencias' ainda não existe no banco. O SQLAlchemy vai criá-la com o modelo novo ao iniciar a app.")
    conn.close()
    exit()

# Verifica se a coluna já existe antes de tentar adicionar
cursor.execute("PRAGMA table_info(transferencias)")
colunas = [row[1] for row in cursor.fetchall()]

if "numero_movimento" not in colunas:
    cursor.execute(
        "ALTER TABLE transferencias ADD COLUMN numero_movimento TEXT DEFAULT NULL"
    )
    conn.commit()
    print("✓ Coluna 'numero_movimento' adicionada com sucesso à tabela 'transferencias'.")
else:
    print("✓ Coluna 'numero_movimento' já existe — nada a fazer.")

conn.close()