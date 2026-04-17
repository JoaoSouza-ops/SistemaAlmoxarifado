from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String)
    email = Column(String, unique=True, index=True)
    senha_hash = Column(String) # NUNCA guardamos a senha real, apenas o hash
    cargo = Column(String) # Ex: 'ADMIN', 'OPERADOR'
    ativo = Column(Boolean, default=True)