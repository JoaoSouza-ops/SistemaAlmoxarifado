# Arquivo: app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Definimos onde o banco vai morar. "sqlite:///./almoxarifado.db" significa
# que ele vai criar um arquivo chamado almoxarifado.db na raiz do projeto.
SQLALCHEMY_DATABASE_URL = "sqlite:///./almoxarifado.db"

# 2. Criamos o "Motor" que vai se conectar ao banco.
# O connect_args é uma exigência específica do SQLite no FastAPI.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Criamos a "Fábrica de Sessões". Cada requisição que chegar na API
# vai pedir uma sessão dessas para conversar com o banco.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Essa é a classe base. Todos os nossos modelos de tabelas vão herdar dela.
Base = declarative_base()

# 5. Função auxiliar para injetarmos o banco de dados nas nossas rotas depois
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()