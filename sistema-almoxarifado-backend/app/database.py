# Arquivo: app/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Carrega as variáveis do ficheiro .env
load_dotenv()

# 2. Busca a URL do ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./almoxarifado.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- ESTA É A FUNÇÃO QUE ESTÁ FALTANDO ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

    