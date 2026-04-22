# Arquivo: app/auth.py
from datetime import datetime, timedelta, timezone
from typing import List
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
import bcrypt
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY                  = os.getenv("SECRET_KEY", "uma_chave_muito_segura_da_prefeitura_123")
ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

ESCOPOS_POR_CARGO = {
    "ADMIN": [
        "patrimonio:read",
        "patrimonio:write",
        "transferencia:write",
        "transferencia:approve",
        "admin:override",
    ],
    "OPERADOR": [
        "patrimonio:read",
        "transferencia:write",
        "transferencia:approve",
    ],
    "VISUALIZADOR": [
        "patrimonio:read",
    ],
}


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha_pura.encode(), senha_hash.encode())


def criar_token_acesso(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def obter_usuario_atual(token: str = Depends(oauth2_scheme)) -> dict:
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise erro
        return {
            "email":   email,
            "cargo":   payload.get("cargo"),
            "escopos": payload.get("escopos", []),
        }
    except JWTError:
        raise erro


def verificar_permissao(escopos_exigidos: List[str]):
    def verificador(usuario: dict = Depends(obter_usuario_atual)):
        escopos_do_usuario: List[str] = usuario.get("escopos", [])
        if not any(e in escopos_do_usuario for e in escopos_exigidos):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type":   "https://api.almoxarifado.gov.br/erros/403",
                    "title":  "Sem permissão",
                    "status": 403,
                    "detail": f"Exige um dos escopos: {escopos_exigidos}. "
                              f"Token contém: {escopos_do_usuario}.",
                },
            )
        return usuario
    return verificador