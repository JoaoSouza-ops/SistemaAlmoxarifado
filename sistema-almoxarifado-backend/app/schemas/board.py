from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

# 1. Definimos as categorias permitidas (Isso evita que alguém digite "URGENTE" em vez de "AVISO")
class CategoriaNota(str, Enum):
    AVISO = "AVISO"
    PENDENCIA = "PENDENCIA"
    MANUTENCAO = "MANUTENCAO"

# 2. Criamos o modelo de dados da Nota
class NotaBoard(BaseModel):
    titulo: str = Field(..., max_length=100, description="Título da anotação operacional")
    descricao: Optional[str] = Field(None, description="Detalhes descritivos da nota")
    categoria: CategoriaNota
    fixado: bool = Field(default=False, description="Se true, a nota fica no topo do board")