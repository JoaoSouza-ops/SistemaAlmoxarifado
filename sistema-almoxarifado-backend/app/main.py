# Arquivo: app/main.py
from fastapi import FastAPI
from app.routers import board # Importa o router do board
from app.routers import patrimonio # Importa o router de patrimonio
from app.routers import transferencia # Importa o router de transferencias

# Importamos o motor do banco e os modelos
from app.database import engine
from app.models import board as models_board # Avisos
from app.models import patrimonio as models_patrimonio # Patrimonios
from app.models import transferencia as models_transferencia #transferencia de patrimonios

# Comando que cria as tabelas no banco de dados quando a API sobe
models_board.Base.metadata.create_all(bind=engine) #Avisos
models_patrimonio.Base.metadata.create_all(bind=engine) # Patrimonios
models_transferencia.Base.metadata.create_all(bind=engine) #Patrimonios

app = FastAPI(
    title="API - SGM Almoxarifado",
    description="Backend para gestão de patrimônios e transferências.",
    version="2.0.0"
)

@app.get("/")
def health_check():
    return {"status": "SGM Backend Operacional", "ambiente": "Desenvolvimento"}

app.include_router(board.router) #Conecta o router de Patrimonio a API
app.include_router(patrimonio.router) # Conectar o router de patrimonio a API
app.include_router(transferencia.router) #Conecta o router de transferencia de Patrimonios