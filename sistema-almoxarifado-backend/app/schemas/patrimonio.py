# Arquivo: app/schemas/patrimonio.py
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional
from datetime import datetime

class CamelModel(BaseModel):
    """Base que serializa campos snake_case → camelCase no JSON de saída."""
    model_config = ConfigDict(
        populate_by_name=True, 
        alias_generator=to_camel,
        from_attributes=True
    )

# ─── Histórico ────────────────────────────────────────────────────────────────
class HistoricoBase(CamelModel):
    acao: str
    origem: Optional[str] = None
    destino: Optional[str] = None
    data_hora: datetime # O alias_generator já vai transformar em dataHora automaticamente

# ─── Detalhe do patrimônio ────────────────────────────────────────────────────
class PatrimonioDetalhe(CamelModel):
    numero: str
    descricao: str
    status: str
    setor_atual: str  # CORREÇÃO: Deve ser snake_case para o SQLAlchemy encontrar!

    # CORREÇÃO: Variável chama 'historicos' (como no banco), mas o JSON exibe 'historicoMovimentacoes'
    historicos: List[HistoricoBase] = Field(
        default=[], 
        serialization_alias="historicoMovimentacoes" 
    )

# ─── Cadastro (entrada) ───────────────────────────────────────────────────────
class PatrimonioCriar(CamelModel): # Adicionamos CamelModel aqui também
    numero: str
    descricao: str
    setor_atual: str

# ─── Baixa ────────────────────────────────────────────────────────────────────
class SolicitacaoBaixa(BaseModel):
    justificativa: str = Field(..., min_length=15, description="Motivo detalhado da baixa patrimonial")

# ─── Paginação ────────────────────────────────────────────────────────────────
class PaginacaoMeta(CamelModel): # Mudou para CamelModel
    total_count: int  # CORREÇÃO: snake_case
    current_page: int # CORREÇÃO: snake_case
    next_cursor: Optional[str] = None # CORREÇÃO: snake_case

class PaginatedPatrimonios(CamelModel): # Mudou para CamelModel
    data: List[PatrimonioDetalhe]
    meta: PaginacaoMeta