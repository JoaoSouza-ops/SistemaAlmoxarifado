# Arquivo: app/schemas/board.py
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from enum import Enum
from typing import Optional

class CategoriaNota(str, Enum):
    AVISO = "AVISO"
    PENDENCIA = "PENDENCIA"
    MANUTENCAO = "MANUTENCAO"

class NotaBoard(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    titulo: str = Field(..., max_length=100, description="Título da anotação operacional")
    descricao: Optional[str] = Field(None, description="Detalhes descritivos da nota")
    categoria: CategoriaNota
    fixado: bool = Field(default=False, description="Se true, a nota fica no topo do board")