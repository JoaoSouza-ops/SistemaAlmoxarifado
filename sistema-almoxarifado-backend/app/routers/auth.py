# Arquivo: app/routers/auth.py
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import UsuarioModel
from app.auth import verificar_senha, criar_token_acesso, ESCOPOS_POR_CARGO

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(
        UsuarioModel.email == form_data.username
    ).first()

    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Contate o administrador.",
        )

    # ─── Resolve escopos ──────────────────────────────────────────────────────
    # Prioridade: escopos_override do usuário > padrão do cargo.
    # Isso permite conceder admin:override apenas para usuários específicos
    # sem precisar criar um novo cargo.
    if usuario.escopos_override:
        escopos = json.loads(usuario.escopos_override)
    else:
        escopos = ESCOPOS_POR_CARGO.get(usuario.cargo, [])
    # ─────────────────────────────────────────────────────────────────────────

    token = criar_token_acesso(data={
        "sub":     usuario.email,
        "cargo":   usuario.cargo,   # mantido para retrocompatibilidade
        "escopos": escopos,         # novo — alinha com contrato v2
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "escopos":      escopos,    # retorna para o cliente saber o que pode fazer
    }