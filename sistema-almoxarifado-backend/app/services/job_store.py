# app/services/job_store.py
from enum import Enum
from datetime import datetime, timezone
from uuid import uuid4


# Enum em português conforme esperado pelo router
class StatusEnum(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    ERRO = "ERRO"

# Dicionário global em memória
_jobs: dict[str, dict] = {}

def criar_job() -> str:
    """Cria um novo Job e devolve o seu ID único"""
    job_id = str(uuid4())
    job = {
        "id": job_id,
        "status": StatusEnum.PENDENTE,
        "progresso": 0,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": None,
        "erro": None
    }
    _jobs[job_id] = job
    return job

def atualizar_job(job_id: str, **kwargs) -> None:
    """Atualiza campos de um Job existente"""
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)

def buscar_job(job_id: str) -> dict:
    """Devolve os dados do Job ou None se não existir"""
    return _jobs.get(job_id)