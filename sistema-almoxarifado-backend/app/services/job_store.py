# app/services/job_store.py
from enum import Enum
from datetime import datetime, timezone
import uuid

# Enum em português conforme esperado pelo router
class StatusEnum(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    ERRO = "ERRO"

# Dicionário global em memória
_jobs = {}

def criar_job() -> str:
    """Cria um novo Job e devolve o seu ID único"""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "status": StatusEnum.PENDENTE,
        "progresso": 0,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": None,
        "erro": None
    }
    return job_id

def atualizar_job(job_id: str, status: StatusEnum = None, progresso: int = None, resultado: dict = None, erro: str = None):
    """Atualiza o estado e o progresso de um Job existente"""
    if job_id in _jobs:
        if status:
            _jobs[job_id]["status"] = status
        if progresso is not None:
            _jobs[job_id]["progresso"] = progresso
        if resultado:
            _jobs[job_id]["resultado"] = resultado
        if erro:
            _jobs[job_id]["erro"] = erro

def buscar_job(job_id: str) -> dict:
    """Devolve os dados do Job ou None se não existir"""
    return _jobs.get(job_id)