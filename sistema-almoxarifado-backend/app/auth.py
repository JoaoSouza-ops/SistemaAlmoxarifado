# Arquivo: app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

# Define onde o FastAPI deve buscar o token (na rota de login que criamos)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Configurações de Segurança (No futuro, leve isso para o .env)
SECRET_KEY = os.getenv("SECRET_KEY", "uma_chave_muito_segura_da_prefeitura_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Função para transformar senha em Hash
def hash_senha(senha: str):
    return pwd_context.hash(senha)

# Função para verificar se a senha digitada bate com o Hash
def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

# Função para gerar o Token JWT
def criar_token_acesso(data: dict):
    dados_para_criptografar = data.copy()
    expiracao = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    dados_para_criptografar.update({"exp": expiracao})
    return jwt.encode(dados_para_criptografar, SECRET_KEY, algorithm=ALGORITHM)

def obter_usuario_atual(token: str = Depends(oauth2_scheme)):
    erro_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Putz! Não consegui validar suas credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodifica o token usando a sua SECRET_KEY
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise erro_credenciais
        return {"email": email, "cargo": payload.get("cargo")}
    except JWTError:
        raise erro_credenciais

# Esta função é uma "fábrica" de permissões
def verificar_permissao(cargos_permitidos: list):
    def verificador(usuario: dict = Depends(obter_usuario_atual)):
        if usuario.get("cargo") not in cargos_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Esta ação é exclusiva para: {', '.join(cargos_permitidos)}"
            )
        return usuario
    return verificador