# Arquivo: app/models/patrimonio.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class PatrimonioModel(Base):
    __tablename__ = "patrimonios"

    numero     = Column(String, primary_key=True, index=True)
    descricao  = Column(String, nullable=False)
    status     = Column(String, default="ATIVO")
    setor_atual = Column(String, nullable=False)

    historicos = relationship("HistoricoModel", back_populates="patrimonio")


class HistoricoModel(Base):
    __tablename__ = "historico_movimentacoes"

    id                 = Column(Integer, primary_key=True, index=True)
    patrimonio_numero  = Column(String, ForeignKey("patrimonios.numero"))
    data_hora          = Column(DateTime, default=datetime.now(timezone.utc))
    acao               = Column(String, nullable=False)
    origem             = Column(String, nullable=True)
    destino            = Column(String, nullable=True)

    patrimonio = relationship("PatrimonioModel", back_populates="historicos")