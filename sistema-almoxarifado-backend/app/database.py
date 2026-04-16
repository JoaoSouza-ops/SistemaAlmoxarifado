import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Carrega as variáveis do ficheiro .env para o sistema
load_dotenv()

# 2. Busca a URL do ambiente, com um valor padrão caso não encontre
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./default.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
# ... o resto continua igual