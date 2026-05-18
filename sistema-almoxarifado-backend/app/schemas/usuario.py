from pydantic import BaseModel, EmailStr
from typing import Optional

class UsuarioCriar(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: str
    cargo: str  # 'ADMIN' | 'OPERADOR' | 'VISUALIZADOR'

class UsuarioEditar(BaseModel):
    nome_completo: Optional[str]  = None
    cargo:         Optional[str]  = None
    nova_senha:    Optional[str]  = None
    ativo:         Optional[bool] = None

class UsuarioResposta(BaseModel):
    id:            int
    nome_completo: str
    email:         str
    cargo:         str
    ativo:         bool

    model_config = {"from_attributes": True}