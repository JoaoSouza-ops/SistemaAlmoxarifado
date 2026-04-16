# Arquivo: app/schemas/transferencia.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum

# 1. Criamos um Enum blindado com as únicas duas opções possíveis
class DecisaoTransferencia(str, Enum):
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"

class SolicitacaoTransferencia(BaseModel):
    patrimonio_numero: str
    setor_destino: str
    responsavel_recebimento: str
    justificativa: str

class AprovacaoTransferencia(BaseModel):
    # 2. Trocamos o 'str' por nosso Enum
    decisao: DecisaoTransferencia 
    override_admin: bool = False
    motivo_override: Optional[str] = None