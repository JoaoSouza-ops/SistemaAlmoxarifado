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
class PatrimonioCriar(CamelModel):
    numero:      str = Field(..., min_length=5, max_length=10,
                             pattern=r"^\d{5,6}$",
                             description="5 ou 6 dígitos numéricos")
    descricao:   str = Field(..., min_length=3, max_length=200)
    setor_atual: str = Field(..., min_length=1, max_length=100)

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