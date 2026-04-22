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


# O alias_generator converte snake_case → camelCase no JSON (entrada e saída).
# O atributo Python permanece snake_case — o router DEVE usar snake_case.
# JSON aceito: {"patrimonioId": ..., "setorDestino": ..., "responsavelRecebimento": ...}
# Atributo Python: .patrimonio_id, .setor_destino, .responsavel_recebimento
class SolicitacaoTransferencia(BaseSchema):
    patrimonio_id:            str = Field(..., description="Número/ID do patrimônio a transferir")
    setor_destino:            str = Field(..., description="ID do setor de destino")
    responsavel_recebimento:  str = Field(..., description="Nome do responsável no destino")
    justificativa:            Optional[str] = Field(
        None, min_length=10, max_length=500,
        description="Motivo da transferência"
    )


# JSON aceito: {"decisao": ..., "overrideAdmin": ..., "motivoOverride": ...}
# Atributo Python: .decisao, .override_admin, .motivo_override
class AprovacaoTransferencia(BaseSchema):
    decisao:         DecisaoTransferencia
    override_admin:  bool = Field(default=False,
                                  description="Requer escopo admin:override no JWT.")
    motivo_override: Optional[str] = Field(
        None, min_length=15,
        description="Obrigatório quando overrideAdmin=true"
    )