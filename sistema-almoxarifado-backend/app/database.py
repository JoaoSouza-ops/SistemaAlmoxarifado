# Arquivo: app/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Carrega as variáveis do ficheiro .env
load_dotenv()

# 2. Busca a URL do ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./almoxarifado.db")

# Lógica de Tuning Dinâmico
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Configuração humilde para SQLite local
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # 🚀 CONFIGURAÇÃO DE FÓRMULA 1 PARA POSTGRESQL 🚀
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=50,          # Mantém até 50 conexões abertas e prontas a usar
        max_overflow=50,       # Se houver um pico, permite criar mais 50 conexões temporárias
        pool_timeout=30        # Espera até 30 segundos na fila antes de dar Erro 500
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# ... (o resto mantém-se)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()