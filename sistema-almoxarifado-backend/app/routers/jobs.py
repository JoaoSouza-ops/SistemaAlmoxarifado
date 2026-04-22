# Arquivo: app/routers/jobs.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Estado centralizado em módulo neutro — sem ciclo de import
from app.services.job_store import StatusEnum, buscar_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobStatus(BaseModel):
    jobId:    str
    status:   StatusEnum
    progress: int = 0


# ─── GET /jobs/{id} — Contrato v2, schema JobStatus ──────────────────────────
# 1. A ROTA E A FUNÇÃO TÊM DE TER O MESMO NOME DE VARIÁVEL: {job_id}
@router.get("/{job_id}")  # Se o router não tiver prefixo /jobs, use "/jobs/{job_id}"
def consultar_job(job_id: str):
    
    job = buscar_job(job_id)
    if not job:
        # Se não encontrar, agora sim devolverá 404!
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    # 2. O CONTRATO EXIGE CAMEL CASE: "jobId", "createdAt", etc.
    # O Pydantic nos testes vai validar este dicionário com sucesso.
    return {
        "jobId": job["id"],               # camelCase (Obrigatório no Contrato)
        "status": job["status"],
        "progress": job["progresso"],
        "createdAt": job["criado_em"],    # camelCase
        "result": job["resultado"],
        "error": job["erro"]
    }
