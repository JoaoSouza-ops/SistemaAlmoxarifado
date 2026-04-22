# tests/test_transferencia.py
"""
Testes do ciclo de vida de transferências.
Cobre: criação, aprovação, rejeição, override admin,
       regras de negócio, bloqueio de patrimônio em trânsito.
"""
import pytest


PAYLOAD_TRANSFERENCIA = {
    "patrimonioId": "2026-000001",
    "setorDestino": "SETOR-FINANCEIRO",
    "responsavelRecebimento": "Ana Souza",
    "justificativa": "Necessidade operacional urgente do setor",
}


class TestSolicitacaoTransferencia:
    def test_solicitar_cria_transferencia_e_bloqueia_patrimonio(
        self, client, h_operador, patrimonio_ativo, db
    ):
        from app.models.transferencia import TransferenciaModel
        r = client.post("/transferencias/", json=PAYLOAD_TRANSFERENCIA, headers=h_operador)
        assert r.status_code == 201
        # patrimônio deve estar bloqueado
        db.refresh(patrimonio_ativo)
        assert patrimonio_ativo.status == "TRANSFERENCIA_PENDENTE"
        # registro criado no banco
        t = db.query(TransferenciaModel).filter(
            TransferenciaModel.patrimonio_numero == patrimonio_ativo.numero
        ).first()
        assert t is not None
        assert t.status == "PENDENTE"
        assert t.setor_destino == "SETOR-FINANCEIRO"

    def test_transferencia_patrimonio_inexistente_retorna_404(self, client, h_operador):
        r = client.post("/transferencias/", json={
            **PAYLOAD_TRANSFERENCIA,
            "patrimonioId": "NAOEXISTE",
        }, headers=h_operador)
        assert r.status_code == 404
        assert r.headers["content-type"] == "application/problem+json"

    def test_transferencia_patrimonio_ja_pendente_retorna_422(
        self, client, h_operador, patrimonio_pendente
    ):
        p, _ = patrimonio_pendente
        r = client.post("/transferencias/", json={
            **PAYLOAD_TRANSFERENCIA,
            "patrimonioId": p.numero,
        }, headers=h_operador)
        assert r.status_code == 422
        assert r.headers["content-type"] == "application/problem+json"

    def test_transferencia_patrimonio_baixado_retorna_422(
        self, client, h_operador, patrimonio_baixado
    ):
        r = client.post("/transferencias/", json={
            **PAYLOAD_TRANSFERENCIA,
            "patrimonioId": patrimonio_baixado.numero,
        }, headers=h_operador)
        assert r.status_code == 422

    def test_transferencia_justificativa_curta_retorna_422(
        self, client, h_operador, patrimonio_ativo
    ):
        r = client.post("/transferencias/", json={
            **PAYLOAD_TRANSFERENCIA,
            "justificativa": "curta",
        }, headers=h_operador)
        assert r.status_code == 422

    def test_transferencia_sem_permissao_retorna_403(self, client, h_visualizador, patrimonio_ativo):
        r = client.post("/transferencias/", json=PAYLOAD_TRANSFERENCIA, headers=h_visualizador)
        assert r.status_code == 403


class TestAprovacaoTransferencia:
    def test_aprovacao_move_patrimonio_e_registra_historico(
        self, client, h_admin, patrimonio_pendente, db
    ):
        from app.models.patrimonio import PatrimonioModel, HistoricoModel
        p, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA",
        }, headers=h_admin)
        assert r.status_code == 200
        # patrimônio deve estar ATIVO no setor de destino
        db.refresh(p)
        assert p.status == "ATIVO"
        assert p.setor_atual == t.setor_destino
        # histórico registrado
        h = db.query(HistoricoModel).filter(
            HistoricoModel.patrimonio_numero == p.numero,
            HistoricoModel.acao == "TRANSFERENCIA_APROVADA",
        ).first()
        assert h is not None

    def test_rejeicao_destrava_patrimonio(
        self, client, h_admin, patrimonio_pendente, db
    ):
        p, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "REJEITADA",
        }, headers=h_admin)
        assert r.status_code == 200
        db.refresh(p)
        assert p.status == "ATIVO"
        db.refresh(t)
        assert t.status == "REJEITADA"

    def test_aprovacao_ja_processada_retorna_422(
        self, client, h_admin, patrimonio_pendente
    ):
        _, t = patrimonio_pendente
        # primeira aprovação
        client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA"
        }, headers=h_admin)
        # segunda tentativa
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA"
        }, headers=h_admin)
        assert r.status_code == 422

    def test_override_admin_sem_motivo_retorna_422(
        self, client, h_admin, patrimonio_pendente
    ):
        _, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA",
            "overrideAdmin": True,
            # motivoOverride ausente
        }, headers=h_admin)
        assert r.status_code == 422
        assert r.headers["content-type"] == "application/problem+json"

    def test_override_admin_com_motivo_registra_acao_especial(
        self, client, h_admin, patrimonio_pendente, db
    ):
        from app.models.patrimonio import HistoricoModel
        p, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA",
            "overrideAdmin": True,
            "motivoOverride": "Autorização especial da diretoria para urgência operacional",
        }, headers=h_admin)
        assert r.status_code == 200
        h = db.query(HistoricoModel).filter(
            HistoricoModel.patrimonio_numero == p.numero,
            HistoricoModel.acao == "TRANSFERENCIA_FORCADA_ADMIN",
        ).first()
        assert h is not None

    def test_aprovacao_por_operador_e_permitida(
        self, client, h_operador, patrimonio_pendente
    ):
        # operador tem transferencia:approve
        _, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "REJEITADA",
        }, headers=h_operador)
        assert r.status_code == 200

    def test_aprovacao_por_visualizador_retorna_403(
        self, client, h_visualizador, patrimonio_pendente
    ):
        _, t = patrimonio_pendente
        r = client.post(f"/transferencias/{t.id}/aprovacoes", json={
            "decisao": "APROVADA",
        }, headers=h_visualizador)
        assert r.status_code == 403

    def test_transferencia_inexistente_retorna_422(self, client, h_admin):
        r = client.post("/transferencias/999999/aprovacoes", json={
            "decisao": "APROVADA",
        }, headers=h_admin)
        assert r.status_code == 422