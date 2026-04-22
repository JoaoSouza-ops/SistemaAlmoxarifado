# Arquivo: app/main.py  (versão final após todas as correções)
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import board
from app.routers import patrimonio
from app.routers import transferencia
from app.routers import auth
from app.routers import jobs    # CORREÇÃO 2: polling assíncrono
from app.routers import setores # CORREÇÃO 4: listagem por setor

from app.database import engine
from app.models import board as models_board
from app.models import patrimonio as models_patrimonio
from app.models import transferencia as models_transferencia
from app.models import usuario as models_usuario

from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError



models_board.Base.metadata.create_all(bind=engine)
models_patrimonio.Base.metadata.create_all(bind=engine)
models_transferencia.Base.metadata.create_all(bind=engine)
models_usuario.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API - SGM Almoxarifado (Gestão de Patrimônios)",
    description="API RESTful orientada a serviços para gestão de inventário e transferências.",
    version="2.0.0",
)

# ... (seu código app = FastAPI(...) ) ...

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Transforma os erros HTTP do FastAPI no padrão RFC 7807"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": "Erro na requisição",
            "status": exc.status_code,
            "detail": str(exc.detail)
        },
        media_type="application/problem+json"
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Transforma erros do Pydantic no padrão RFC 7807"""
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Erro de Validação",
            "status": 422,
            "detail": exc.errors()
        },
        media_type="application/problem+json"
    )

# ─── MIDDLEWARE: X-Correlation-ID ─────────────────────────────────────────────
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

app.add_middleware(CorrelationIDMiddleware)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "SGM Backend Operacional", "versao": "2.0.0"}

app.include_router(board.router)
app.include_router(patrimonio.router)
app.include_router(transferencia.router)
app.include_router(setores.router)
app.include_router(jobs.router)
app.include_router(auth.router)