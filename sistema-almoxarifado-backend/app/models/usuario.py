# Arquivo: app/models/usuario.py
from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id             = Column(Integer, primary_key=True, index=True)
    nome_completo  = Column(String)
    email          = Column(String, unique=True, index=True)
    senha_hash     = Column(String)
    cargo          = Column(String)   # 'ADMIN' | 'OPERADOR' | 'VISUALIZADOR'
    ativo          = Column(Boolean, default=True)

    # ─── Escopos customizados por usuário ─────────────────────────────────────
    # Armazena lista JSON: '["patrimonio:read", "transferencia:write"]'
    # Se NULL, o login usa os escopos padrão do cargo (ESCOPOS_POR_CARGO em auth.py).
    # Útil para conceder ou restringir escopos individuais sem mudar o cargo.
    escopos_override = Column(String, nullable=True)