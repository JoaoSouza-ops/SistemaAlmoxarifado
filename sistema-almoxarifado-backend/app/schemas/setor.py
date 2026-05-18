# app/schemas/setor.py
from pydantic import BaseModel, Field

class SetorBase(BaseModel):
    nome: str = Field(..., min_length=3, description="Nome completo do setor")
    sigla: str = Field(..., min_length=2, description="Sigla do setor")

class SetorCriar(SetorBase):
    id: str = Field(..., description="ID único. Ex: SETOR-RH")

class SetorAtualizar(BaseModel):
    nome: str | None = None
    sigla: str | None = None

class SetorRead(SetorBase):
    id: str

    class Config:
        from_attributes = True