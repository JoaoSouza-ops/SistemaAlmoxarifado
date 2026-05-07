# Arquivo: app/schemas/transferencia.py
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from enum import Enum
from datetime import datetime


class DecisaoTransferencia(str, Enum):
    APROVADA  = "APROVADA"
    REJEITADA = "REJEITADA"


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class SolicitacaoTransferencia(BaseSchema):
    patrimonio_id:            str           = Field(..., pattern=r"\d{5,6}$",
                                                    description="Formatos aceitos: 12345 123456 ou AAAA-123456")
    setor_destino:            str           = Field(..., description="ID do setor de destino")
    responsavel_recebimento:  str           = Field(..., description="Nome do responsável no destino")
    justificativa:            Optional[str] = Field(None, min_length=10, max_length=500, description="Motivo")
    numero_movimento:         Optional[str] = Field(None, max_length=50, description="Nº do movimento oficial")


class AprovacaoTransferencia(BaseSchema):
    decisao:         DecisaoTransferencia
    override_admin:  bool           = Field(default=False, description="Requer o escopo admin:override no JWT")
    motivo_override: Optional[str]  = Field(None, min_length=15, max_length=500)


class EdicaoTransferencia(BaseSchema):
    setor_destino:            Optional[str] = Field(None, description="UUID do setor de destino")
    responsavel_recebimento:  Optional[str] = Field(None, min_length=3, max_length=150)
    justificativa:            Optional[str] = Field(None, min_length=10, max_length=500)
    numero_movimento:         Optional[str] = Field(None, max_length=50)
    override_admin:           bool           = Field(default=False)
    motivo_override:          Optional[str]  = Field(None, min_length=15, max_length=500)


class AssinaturaTransferencia(BaseSchema):
    papel: str = Field(..., description="Deve ser TRANSFERIDOR ou RECEBEDOR")


# ─── Schema de leitura (resposta da API) ──────────────────────────────────────
#
# FIX: from_attributes=True é obrigatório para que FastAPI consiga serializar
# instâncias SQLAlchemy quando este schema é usado como response_model.
# Sem isso, Pydantic v2 lança ValidationError ao tentar acessar os atributos
# do modelo ORM.
#
# FIX: adicionados justificativa e efetivado_em, que estavam ausentes e faziam
# esses campos sumirem de todas as respostas da API.

class TransferenciaRead(BaseSchema):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,          # ← obrigatório para ORM → Pydantic
    )

    id:                          int
    patrimonio_numero:           str
    setor_origem:                str
    setor_destino:               str
    responsavel_recebimento:     str
    status:                      str
    data_solicitacao:            datetime
    justificativa:               Optional[str]      = None   # ← estava ausente
    efetivado_em:                Optional[datetime] = None   # ← estava ausente
    numero_movimento:            Optional[str]      = None
    assinatura_transferidor_em:  Optional[datetime] = None
    assinatura_recebedor_em:     Optional[datetime] = None