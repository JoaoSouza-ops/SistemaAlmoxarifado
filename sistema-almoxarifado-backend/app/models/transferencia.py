# Arquivo: app/models/transferencia.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.database import Base

class TransferenciaModel(Base):
    __tablename__ = "transferencias"

    id = Column(Integer, primary_key=True, index=True)
    patrimonio_numero = Column(String, ForeignKey("patrimonios.numero"))
    setor_origem = Column(String, nullable=False)
    setor_destino = Column(String, nullable=False)
    responsavel_recebimento = Column(String, nullable=False)
    justificativa = Column(String)
    
    # Status pode ser: PENDENTE, APROVADA ou REJEITADA
    status = Column(String, default="PENDENTE") 
    data_solicitacao = Column(DateTime, default=datetime.utcnow)