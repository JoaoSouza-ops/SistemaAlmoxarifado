# Arquivo: app/schemas/patrimonio.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Schema para mostrar o histórico (Saída de dados)
class HistoricoBase(BaseModel):
    acao: str
    origem: Optional[str] = None
    destino: Optional[str] = None
    data_hora: datetime

    # Isso diz ao Pydantic para ler os dados direto do SQLAlchemy
    class Config:
        from_attributes = True

# Schema para cadastrar um item novo (Entrada de dados)
class PatrimonioCriar(BaseModel):
    numero: str
    descricao: str
    setor_atual: str

# Schema completo que devolve o item + a lista de históricos (Saída de dados)
class PatrimonioDetalhe(BaseModel):
    numero: str
    descricao: str
    status: str
    setor_atual: str
    historicos: List[HistoricoBase] = [] # Aqui aninhamos o histórico!

    class Config:
        from_attributes = True

class SolicitacaoBaixa(BaseModel):
    justificativa: str = Field(..., min_length=15, description="Motivo detalhado da baixa patrimonial")