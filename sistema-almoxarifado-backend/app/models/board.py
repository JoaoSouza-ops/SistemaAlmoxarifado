# Arquivo: app/models/board.py
from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

# Esta classe representa a Tabela física no banco de dados
class NotaBoardModel(Base):
    __tablename__ = "notas_board" # Nome da tabela no banco

    # Definimos as colunas
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descricao = Column(String, nullable=True)
    categoria = Column(String(50), nullable=False)
    fixado = Column(Boolean, default=False)