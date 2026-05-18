# tests/test_regressoes.py
#
# CORREÇÃO: removido `from tests.conftest import auth`
# O helper `auth()` agora está definido localmente neste arquivo.

import pytest
from app.models.patrimonio    import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.services.job_store   import criar_job, buscar_job, atualizar_job, StatusEnum


# ─── Helper local — monta o header Authorization ─────────────────────────────

def auth(token: str) -> dict:
    """Retorna o header Authorization pronto para usar no TestClient."""
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# BUG 2 — Jobs retornavam 404 mesmo após importação bem-sucedida (202)
# ══════════════════════════════════════════════════════════════════════════════

class TestBug2_JobsNaoEncontrados:
    """
    ANTES DA CORREÇÃO:
      - POST /patrimonios/importacoes → 202 + Location: /jobs/XYZ
      - GET /jobs/XYZ → 404 (rota não registrada / job_store inexistente)

    DEPOIS DA CORREÇÃO:
      - job_store.py criado com criar_job(), buscar_job(), atualizar_job()
      - jobs.router registrado no main.py
      - Ciclo completo funciona
    """

    def test_criar_job_retorna_estrutura_completa(self):
        job = criar_job()
        assert "id"        in job
        assert "status"    in job
        assert "progresso" in job
        assert "criado_em" in job
        assert "resultado" in job
        assert "erro"      in job

    def test_criar_job_status_inicial_e_pendente(self):
        job = criar_job()
        assert job["status"]    == StatusEnum.PENDENTE
        assert job["progresso"] == 0
        assert job["resultado"] is None
        assert job["erro"]      is None

    def test_buscar_job_retorna_job_criado(self):
        job = criar_job()
        encontrado = buscar_job(job["id"])
        assert encontrado is not None, "buscar_job() retornou None para um job existente"
        assert encontrado["id"] == job["id"]

    def test_buscar_job_inexistente_retorna_none(self):
        assert buscar_job("id-que-nao-existe-jamais") is None

    def test_cada_job_tem_id_unico(self):
        a = criar_job()
        b = criar_job()
        assert a["id"] != b["id"]

    def test_atualizar_job_para_processando(self):
        job = criar_job()
        atualizar_job(job["id"], status=StatusEnum.PROCESSANDO, progresso=50)
        atualizado = buscar_job(job["id"])
        assert atualizado["status"]    == StatusEnum.PROCESSANDO
        assert atualizado["progresso"] == 50

    def test_atualizar_job_para_concluido(self):
        job = criar_job()
        atualizar_job(job["id"], status=StatusEnum.CONCLUIDO, progresso=100,
                      resultado={"importados": 42, "erros": 0})
        c = buscar_job(job["id"])
        assert c["status"]                  == StatusEnum.CONCLUIDO
        assert c["resultado"]["importados"] == 42

    def test_atualizar_job_para_erro(self):
        job = criar_job()
        atualizar_job(job["id"], status=StatusEnum.ERRO, erro="CSV inválido na linha 3.")
        assert "linha 3" in buscar_job(job["id"])["erro"]

    def test_atualizar_job_inexistente_nao_levanta_excecao(self):
        atualizar_job("nao-existe", status=StatusEnum.ERRO)  # sem crash

    def test_rota_get_job_retorna_200(self, client, token_admin):
        """REGRESSÃO: GET /jobs/{id} deve existir após o router ser registrado."""
        job = criar_job()
        res = client.get(f"/jobs/{job['id']}", headers=auth(token_admin))
        assert res.status_code == 200, (
            f"GET /jobs/{job['id']} retornou {res.status_code}. "
            "Verifique se jobs.router está em app/main.py."
        )
        assert res.json()["jobId"] == job["id"]

    def test_rota_get_job_retorna_404_para_id_inexistente(self, client, token_admin):
        res = client.get("/jobs/id-absolutamente-inexistente", headers=auth(token_admin))
        assert res.status_code == 404

    def test_ciclo_completo_importacao(self, client, token_admin):
        """
        Simula o fluxo exato do frontend:
        1. POST /patrimonios/importacoes → 202 + header Location
        2. GET /jobs/{id} → 200

        REGRESSÃO: o passo 2 retornava 404 antes da correção.
        """
        import io
        csv = b"numero,descricao,setor\n2024-100001,Cadeira,SETOR-ADM\n"

        res_import = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("lote.csv", io.BytesIO(csv), "text/csv")},
            headers=auth(token_admin),
        )
        assert res_import.status_code == 202
        assert "location" in res_import.headers, (
            "Resposta 202 deve ter header 'Location' com o caminho do job."
        )

        location = res_import.headers["location"]
        job_id   = location.rstrip("/").split("/")[-1]

        res_job = client.get(f"/jobs/{job_id}", headers=auth(token_admin))
        assert res_job.status_code == 200, (
            f"REGRESSÃO BUG 2: GET {location} retornou {res_job.status_code}. "
            "A rota de jobs não está acessível."
        )
        assert res_job.json()["jobId"] == job_id


# ══════════════════════════════════════════════════════════════════════════════
# BUG 3 — 409 falso positivo ao EDITAR uma transferência pendente
# ══════════════════════════════════════════════════════════════════════════════

class TestBug3_FalsoPositivo409:
    """
    ANTES: PATCH /transferencias/{id} sempre retornava 409 ao editar
           campos estruturais de uma transferência PENDENTE.
    DEPOIS: só retorna 409 se houver OUTRA transferência pendente para
            o mesmo patrimônio.
    """

    @pytest.fixture()
    def transferencia_id(self, db, client, token_admin) -> int:
        """Cria patrimônio + transferência e devolve o ID da transferência."""
        db.add(PatrimonioModel(
            numero="2024-PATCH-001",
            descricao="Notebook teste",
            setor_atual="SETOR-TI",
            status="ATIVO",
        ))
        db.commit()

        res = client.post("/transferencias/", json={
            "patrimonio_id":           "2024-PATCH-001",
            "setor_destino":           "SETOR-RH",
            "responsavel_recebimento": "Carlos Silva",
            "justificativa":           "Realocação aprovada.",
        }, headers=auth(token_admin))

        assert res.status_code == 201, f"Setup falhou: {res.status_code} {res.json()}"
        body = res.json()
        return body.get("id") or body.get("transferencia_id")

    def test_editar_propria_transferencia_nao_retorna_409(
        self, client, token_admin, transferencia_id
    ):
        """REGRESSÃO PRINCIPAL: editar a própria transferência deve retornar 200."""
        res = client.patch(f"/transferencias/{transferencia_id}", json={
            "setor_destino":           "SETOR-ADM",
            "responsavel_recebimento": "Ana Costa",
            "override_admin":          True,
            "motivo_override":         "Correção solicitada pelo gestor do setor.",
        }, headers=auth(token_admin))

        assert res.status_code == 200, (
            f"REGRESSÃO BUG 3: retornou {res.status_code} — {res.json()}\n"
            "Verifique _patrimonio_em_outra_transferencia() em transferencia.py."
        )

    def test_editar_numero_movimento_sem_override_retorna_200(
        self, client, token_operador, transferencia_id
    ):
        """Campo não-estrutural (numeroMovimento) não exige overrideAdmin."""
        res = client.patch(f"/transferencias/{transferencia_id}", json={
            "numero_movimento": "MOV-2024-9999",
        }, headers=auth(token_operador))
        assert res.status_code == 200

    def test_segunda_transferencia_mesmo_patrimonio_e_bloqueada(
        self, client, token_admin, transferencia_id
    ):
        """409/422 legítimo: segundo POST para o mesmo patrimônio deve ser bloqueado."""
        res = client.post("/transferencias/", json={
            "patrimonio_id":           "2024-PATCH-001",
            "setor_destino":           "SETOR-FINANCEIRO",
            "responsavel_recebimento": "Pedro Alves",
        }, headers=auth(token_admin))
        assert res.status_code in (409, 422)

    def test_campo_estrutural_sem_override_retorna_403(
        self, client, token_operador, transferencia_id
    ):
        res = client.patch(f"/transferencias/{transferencia_id}", json={
            "setor_destino":  "SETOR-ADM",
            "override_admin": False,
        }, headers=auth(token_operador))
        assert res.status_code == 403

    def test_edicao_apos_aprovacao_retorna_409(
        self, client, token_admin, transferencia_id
    ):
        """409 legítimo: campo estrutural em transferência já APROVADA."""
        client.post(f"/transferencias/{transferencia_id}/aprovacoes", json={
            "decisao": "APROVADA", "override_admin": False,
        }, headers=auth(token_admin))

        res = client.patch(f"/transferencias/{transferencia_id}", json={
            "setor_destino":   "SETOR-ADM",
            "override_admin":  True,
            "motivo_override": "Tentativa pós-aprovação.",
        }, headers=auth(token_admin))
        assert res.status_code == 409

    def test_motivo_override_curto_retorna_422(
        self, client, token_admin, transferencia_id
    ):
        res = client.patch(f"/transferencias/{transferencia_id}", json={
            "setor_destino":   "SETOR-ADM",
            "override_admin":  True,
            "motivo_override": "curto",
        }, headers=auth(token_admin))
        assert res.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Helper interno — testa _patrimonio_em_outra_transferencia diretamente
# ══════════════════════════════════════════════════════════════════════════════

class TestHelperConflito:

    @pytest.fixture()
    def patrimonio_e_transferencia(self, db):
        p = PatrimonioModel(
            numero="2024-HELPER-001", descricao="Item helper",
            setor_atual="SETOR-TI", status="TRANSFERENCIA_PENDENTE",
        )
        db.add(p)
        db.commit()

        t = TransferenciaModel(
            patrimonio_numero="2024-HELPER-001",
            setor_origem="SETOR-TI", setor_destino="SETOR-RH",
            responsavel_recebimento="Teste", status="PENDENTE",
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return p, t

    def test_sem_ignorar_detecta_conflito(self, db, patrimonio_e_transferencia):
        from app.routers.transferencia import _patrimonio_em_outra_transferencia
        _, t = patrimonio_e_transferencia
        assert _patrimonio_em_outra_transferencia(db, "2024-HELPER-001") is True

    def test_ignorando_proprio_id_sem_conflito(self, db, patrimonio_e_transferencia):
        from app.routers.transferencia import _patrimonio_em_outra_transferencia
        _, t = patrimonio_e_transferencia
        assert _patrimonio_em_outra_transferencia(
            db, "2024-HELPER-001", ignorar_id=t.id
        ) is False

    def test_segunda_transferencia_detectada_ao_ignorar_primeira(
        self, db, patrimonio_e_transferencia
    ):
        from app.routers.transferencia import _patrimonio_em_outra_transferencia
        _, t1 = patrimonio_e_transferencia

        t2 = TransferenciaModel(
            patrimonio_numero="2024-HELPER-001",
            setor_origem="SETOR-TI", setor_destino="SETOR-ADM",
            responsavel_recebimento="Outro", status="PENDENTE",
        )
        db.add(t2)
        db.commit()

        assert _patrimonio_em_outra_transferencia(
            db, "2024-HELPER-001", ignorar_id=t1.id
        ) is True