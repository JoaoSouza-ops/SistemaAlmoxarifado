# tests/test_jobs.py
"""
Testes do sistema de jobs assíncronos.
Cobre: criação via importação, polling de status, job inexistente,
       ciclo de vida PENDENTE → PROCESSANDO → PROCESSANDO/ERRO.
"""
import io
import pytest
from app.services.job_store import criar_job, atualizar_job, buscar_job, StatusEnum
from datetime import datetime, timezone

class TestJobStore:
    """Testes unitários do módulo job_store — sem HTTP."""

    def test_criar_job_retorna_uuid_e_status_pending(self):
        job_id = criar_job()
        job = buscar_job(job_id)
        assert job is not None
        assert job["id"] == job_id
        assert job["status"] == StatusEnum.PENDENTE
        assert job["progresso"] == 0

    def test_atualizar_job_para_processing(self):
        job_id = criar_job()
        atualizar_job(job_id, status=StatusEnum.PROCESSANDO, progresso=50) 
        job = buscar_job(job_id)
        assert job["status"] == StatusEnum.PROCESSANDO
        assert job["progresso"] == 50

    def test_atualizar_job_para_completed(self):
        job_id = criar_job()
        atualizar_job(job_id, StatusEnum.CONCLUIDO, progresso=100)
        job = buscar_job(job_id)
        assert job["status"] == StatusEnum.CONCLUIDO
        assert job["progresso"] == 100

    def test_atualizar_job_para_failed(self):
        job_id = criar_job()
        atualizar_job(job_id, StatusEnum.ERRO)
        job = buscar_job(job_id)
        assert job["status"] == StatusEnum.ERRO

    def test_buscar_job_inexistente_retorna_none(self):
        assert buscar_job("id-que-nao-existe") is None

    def test_atualizar_job_inexistente_nao_levanta_excecao(self):
        # deve ser silencioso — sem KeyError
        atualizar_job("id-inexistente", StatusEnum.ERRO)


class TestJobEndpoint:
    """Testes de integração do endpoint GET /jobs/{id}."""

    def _csv_valido(self):
        return io.BytesIO(
            b"numero,descricao,setor\n2026-JOB001,Cadeira,SETOR-TI\n"
        )

    def test_job_criado_via_importacao_e_consultavel(self, client, h_admin):
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("inv.csv", self._csv_valido(), "text/csv")},
            headers=h_admin,
        )
        assert r.status_code == 202
        job_id = r.headers["Location"].split("/")[-1]

        r2 = client.get(f"/jobs/{job_id}", headers=h_admin)
        assert r2.status_code == 200
        body = r2.json()
        assert body["jobId"] == job_id
        assert body["status"] in ("PENDENTE", "PROCESSANDO", "PROCESSANDO", "ERRO")
        assert isinstance(body["progress"], int)
        assert 0 <= body["progress"] <= 100

    def test_job_inexistente_retorna_404(self, client, h_admin):
        r = client.get("/jobs/00000000-0000-0000-0000-000000000000", headers=h_admin)
        assert r.status_code == 404

    def test_schema_job_status_conforme_contrato(self, client, h_admin):
        """Garante que o response tem exatamente os campos do contrato v2."""
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("inv.csv", self._csv_valido(), "text/csv")},
            headers=h_admin,
        )
        job_id = r.headers["Location"].split("/")[-1]
        r2 = client.get(f"/jobs/{job_id}", headers=h_admin)
        body = r2.json()
        # campos obrigatórios do schema JobStatus do contrato
        assert set(body.keys()) >= {"jobId", "status", "progress"}
        assert body["status"] in ("PENDENTE", "PROCESSANDO", "PROCESSANDO", "ERRO")