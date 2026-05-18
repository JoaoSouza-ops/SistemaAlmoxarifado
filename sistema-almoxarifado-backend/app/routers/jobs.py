# Arquivo: app/routers/jobs.py
#
# CORREÇÃO APLICADA — Jobs 404 no Frontend:
#
# O arquivo jobs.py em si estava correto. O problema era externo:
# a rota nunca foi REGISTRADA no app. Veja a seção
# "O QUE VOCÊ PRECISA FAZER EM main.py" abaixo.
#
# Além disso, o `job_store.py` provavelmente não existia ou não tinha
# a função `buscar_job`. A seção "CRIE O ARQUIVO app/services/job_store.py"
# dá o código completo.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.services.job_store import StatusEnum, buscar_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobStatus(BaseModel):
    jobId:     str
    status:    StatusEnum
    progress:  int = 0
    createdAt: str | None = None
    result:    Any | None = None
    error:     str | None = None


@router.get("/{job_id}", response_model=JobStatus)
def consultar_job(job_id: str):
    """
    Retorna o status de um job assíncrono (ex: importação de CSV).
    Chamado pelo frontend depois de receber o header Location em um 202.
    """
    job = buscar_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' não encontrado.")

    return {
        "jobId":     job["id"],
        "status":    job["status"],
        "progress":  job["progresso"],
        "createdAt": job["criado_em"],
        "result":    job["resultado"],
        "error":     job["erro"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# O QUE VOCÊ PRECISA FAZER EM app/main.py
# ══════════════════════════════════════════════════════════════════════════════
#
# Abra app/main.py e adicione as duas linhas marcadas com "# ADICIONE":
#
#   from app.routers import jobs          # ADICIONE
#   from app.routers import patrimonios
#   from app.routers import transferencias
#   # ... outros routers ...
#
#   app = FastAPI(...)
#
#   app.include_router(jobs.router)       # ADICIONE
#   app.include_router(patrimonios.router)
#   app.include_router(transferencias.router)
#   # ... outros routers ...
#
# Depois de adicionar, reinicie o servidor (uvicorn) e teste:
#   curl http://localhost:8000/jobs/ID-QUALQUER
# Deve retornar 404 com {"detail": "Job 'ID-QUALQUER' não encontrado."}
# — isso confirma que a rota está registrada e funcional.
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# CRIE O ARQUIVO app/services/job_store.py (se não existir)
# ══════════════════════════════════════════════════════════════════════════════
#
# Este módulo guarda os jobs em memória (dict). Em produção, use Redis ou banco.
# Copie o código abaixo para: app/services/job_store.py
#
# --------------------------------------------------------------------------
# from enum import Enum
# from datetime import datetime, timezone
# from uuid import uuid4
# from typing import Any
#
# class StatusEnum(str, Enum):
#     PENDENTE    = "PENDENTE"
#     PROCESSANDO = "PROCESSANDO"
#     CONCLUIDO   = "CONCLUIDO"
#     ERRO        = "ERRO"
#
# # Armazenamento em memória (perdido ao reiniciar o servidor)
# _jobs: dict[str, dict] = {}
#
# def criar_job() -> dict:
#     """Cria um novo job e retorna o dicionário completo."""
#     job_id = str(uuid4())
#     job = {
#         "id":        job_id,
#         "status":    StatusEnum.PENDENTE,
#         "progresso": 0,
#         "criado_em": datetime.now(timezone.utc).isoformat(),
#         "resultado": None,
#         "erro":      None,
#     }
#     _jobs[job_id] = job
#     return job
#
# def buscar_job(job_id: str) -> dict | None:
#     """Retorna o job pelo ID, ou None se não existir."""
#     return _jobs.get(job_id)
#
# def atualizar_job(job_id: str, **kwargs) -> None:
#     """Atualiza campos de um job existente."""
#     if job_id in _jobs:
#         _jobs[job_id].update(kwargs)
# --------------------------------------------------------------------------
#
# Depois crie a pasta se não existir:
#   mkdir -p app/services
#   touch app/services/__init__.py
# ══════════════════════════════════════════════════════════════════════════════