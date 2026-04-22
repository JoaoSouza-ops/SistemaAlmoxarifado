# Arquivo: app/schemas/transferencia.py
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from enum import Enum


class DecisaoTransferencia(str, Enum):
    APROVADA  = "APROVADA"
    REJEITADA = "REJEITADA"


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class SolicitacaoTransferencia(BaseSchema):
    patrimonio_id:            str = Field(..., description="Número/ID do patrimônio a transferir")
    setor_destino:            str = Field(..., description="ID do setor de destino")
    responsavel_recebimento:  str = Field(..., description="Nome do responsável no destino")
    justificativa:            Optional[str] = Field(None, min_length=10, max_length=500, description="Motivo")
    # ✨ NOVO CAMPO v2.1.0
    numero_movimento:         Optional[str] = Field(None, max_length=50, description="Nº do movimento oficial")


class AprovacaoTransferencia(BaseSchema):
    decisao:         DecisaoTransferencia
    override_admin:  bool = Field(default=False, description="Requer o escopo admin:override no JWT")
    motivo_override: Optional[str] = Field(None, min_length=15, max_length=500)


# ✨ NOVO SCHEMA v2.1.0 (Todos os campos são opcionais para o PATCH)
class EdicaoTransferencia(BaseSchema):
    setor_destino:            Optional[str] = Field(None, description="UUID do setor de destino")
    responsavel_recebimento:  Optional[str] = Field(None, min_length=3, max_length=150)
    justificativa:            Optional[str] = Field(None, min_length=10, max_length=500)
    numero_movimento:         Optional[str] = Field(None, max_length=50)
    
    override_admin:           bool = Field(default=False)
    motivo_override:          Optional[str] = Field(None, min_length=15, max_length=500)