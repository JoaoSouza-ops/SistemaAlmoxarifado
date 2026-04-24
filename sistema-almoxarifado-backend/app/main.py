# Arquivo: app/main.py — v2.1.0 (com CORS para frontend)
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import board
from app.routers import patrimonio
from app.routers import transferencia
from app.routers import auth
from app.routers import jobs
from app.routers import setores

from app.database import engine
from app.models import board as models_board
from app.models import patrimonio as models_patrimonio
from app.models import transferencia as models_transferencia
from app.models import usuario as models_usuario

models_board.Base.metadata.create_all(bind=engine)
models_patrimonio.Base.metadata.create_all(bind=engine)
models_transferencia.Base.metadata.create_all(bind=engine)
models_usuario.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API - SGM Almoxarifado (Gestão de Patrimônios)",
    description="API RESTful para gestão de inventário e transferências.",
    version="2.1.0",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    # "https://almoxarifado.prefeitura.gov.br",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "Location"],
)

# ─── X-Correlation-ID ─────────────────────────────────────────────────────────
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

app.add_middleware(CorrelationIDMiddleware)

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "SGM Backend Operacional", "versao": "2.1.0"}

app.include_router(board.router)
app.include_router(patrimonio.router)
app.include_router(transferencia.router)
app.include_router(setores.router)
app.include_router(jobs.router)
app.include_router(auth.router)