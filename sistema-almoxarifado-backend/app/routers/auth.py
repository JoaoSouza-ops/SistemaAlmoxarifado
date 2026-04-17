# Arquivo: app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import UsuarioModel # Verifique o caminho do seu modelo
from app.auth import verificar_senha, criar_token_acesso

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Busca o usuário pelo e-mail (o OAuth2 usa o campo 'username')
    usuario = db.query(UsuarioModel).filter(UsuarioModel.email == form_data.username).first()
    
    # 2. Verifica se existe e se a senha bate
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Gera o Token com os dados do usuário
    token_acesso = criar_token_acesso(data={"sub": usuario.email, "cargo": usuario.cargo})
    
    return {"access_token": token_acesso, "token_type": "bearer"}