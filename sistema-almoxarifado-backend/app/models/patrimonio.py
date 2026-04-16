# Arquivo: app/models/patrimonio.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# Tabela principal: Os bens físicos
class PatrimonioModel(Base):
    __tablename__ = "patrimonios"

    # Usaremos o número de tombamento como ID (Ex: 2026-001234)
    numero = Column(String, primary_key=True, index=True) 
    descricao = Column(String, nullable=False)
    status = Column(String, default="ATIVO") # Pode ser ATIVO, PENDENTE ou BAIXADO
    setor_atual = Column(String, nullable=False)

    # Relacionamento: Dizemos ao SQLAlchemy que um patrimônio tem uma lista de históricos
    historicos = relationship("HistoricoModel", back_populates="patrimonio")


# Tabela de trilha de auditoria (NUNCA DELETAREMOS NADA DAQUI)
class HistoricoModel(Base):
    __tablename__ = "historico_movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Chave Estrangeira: Aponta para o 'numero' do patrimônio na tabela acima
    patrimonio_numero = Column(String, ForeignKey("patrimonios.numero"))
    
    data_hora = Column(DateTime, default=datetime.utcnow)
    acao = Column(String, nullable=False) # Ex: "CADASTRO_INICIAL", "TRANSFERENCIA", "BAIXA"
    origem = Column(String, nullable=True)
    destino = Column(String, nullable=True)

    # Relacionamento reverso: Conecta este histórico de volta ao seu patrimônio pai
    patrimonio = relationship("PatrimonioModel", back_populates="historicos")