# Arquivo: app/models/transferencia.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from datetime import datetime, timezone
from app.database import Base

class TransferenciaModel(Base):
    __tablename__ = "transferencias"

    id                     = Column(Integer, primary_key=True, index=True)
    patrimonio_numero      = Column(String, ForeignKey("patrimonios.numero"), nullable=False)
    setor_origem           = Column(String, nullable=False)
    setor_destino          = Column(String, nullable=False)
    responsavel_recebimento = Column(String, nullable=False)
    justificativa          = Column(String, nullable=True)

    # ✨ NOVO CAMPO (Contrato v2.1.0)
    numero_movimento       = Column(String(50), nullable=True)

    # Status conforme enum do contrato v2: PENDENTE | APROVADA | REJEITADA
    status                 = Column(String, default="PENDENTE", nullable=False)
    
    # 🐛 CORREÇÃO DE BUG: Usar lambda para garantir que o SQLite recebe um objeto datetime
    data_solicitacao       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Campos de aprovação — alinhados com AprovacaoTransferencia do contrato v2
    override_admin         = Column(Boolean, default=False)
    motivo_override        = Column(String, nullable=True)