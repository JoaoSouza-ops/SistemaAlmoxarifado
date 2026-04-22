# tests/test_transferencia.py
"""
Testes do ciclo de vida de transferências.
Cobre: criação, aprovação, rejeição, override admin,
       regras de negócio, bloqueio de patrimônio em trânsito.
"""
import pytest
import uuid
from app.models.transferencia import TransferenciaModel

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

class TestEdicaoTransferencia:
    def _preparar_dados(self, client, token, db): # <-- 1. Nome do parâmetro é 'db'


        patrimonio_id = f"MOV-TEST-{uuid.uuid4().hex[:6]}"
        
        client.post("/patrimonios/", json={
            "numero": patrimonio_id, "descricao": "Mesa", "setor_atual": "uuid-setor-a"
        }, headers={"Authorization": f"Bearer {token}"})
        
        client.post("/transferencias/", json={
            "patrimonioId": patrimonio_id,
            "setorDestino": "uuid-setor-b",
            "responsavelRecebimento": "João"
        }, headers={"Authorization": f"Bearer {token}"})
        
        # <-- 2. Usar 'db.query' em vez de 'db_session'
        transferencia = db.query(TransferenciaModel).filter(
            TransferenciaModel.patrimonio_numero == patrimonio_id
        ).first()
        
        return transferencia.id

    def test_get_transferencia_retorna_camel_case(self, client, token_admin, db):
        """Garante que a nova rota GET devolve os dados com numeroMovimento em camelCase"""
        t_id = self._preparar_dados(client, token_admin, db)
        
        r = client.get(f"/transferencias/{t_id}", headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200
        dados = r.json()
        assert "patrimonioId" in dados # Verifica camelCase
        assert "numeroMovimento" in dados

    # ✨ Adicionámos o token_admin nos argumentos
    def test_patch_apenas_numero_movimento_sucesso(self, client, token_operador, token_admin, db):
        """O numeroMovimento pode ser editado por qualquer operador sem override"""
        # Usamos o token_admin APENAS para criar os dados de teste
        t_id = self._preparar_dados(client, token_admin, db) 
        
        # Testamos a ROTA de edição usando o token_operador!
        r = client.patch(
            f"/transferencias/{t_id}", 
            json={"numeroMovimento": "DOC-2026-X"},
            headers={"Authorization": f"Bearer {token_operador}"}
        )
        assert r.status_code == 200
        assert r.json()["numeroMovimento"] == "DOC-2026-X"

    def test_patch_estrutural_sem_override_retorna_403(self, client, token_admin, db):
        """
        REGRA DO CONTRATO: Campos estruturais EXIGEM override_admin=True.
        Este teste VAI FALHAR com o código atual, provando a eficácia do TDD!
        """
        t_id = self._preparar_dados(client, token_admin, db)
        
        r = client.patch(
            f"/transferencias/{t_id}", 
            json={
                "setorDestino": "uuid-setor-secreto", 
                "overrideAdmin": False # Sem override, deve ser bloqueado!
            },
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert r.status_code == 403

    # ✨ Adicionámos o token_admin nos argumentos
    def test_patch_estrutural_com_override_mas_sem_escopo_retorna_403(self, client, token_operador, token_admin, db):
        """Operador tenta usar override, mas não tem o escopo no JWT"""
        # Usamos o token_admin APENAS para criar os dados de teste
        t_id = self._preparar_dados(client, token_admin, db)
        
        # Testamos a ROTA de edição usando o token_operador!
        r = client.patch(
            f"/transferencias/{t_id}", 
            json={
                "justificativa": "Mudança de planos", 
                "overrideAdmin": True,
                "motivoOverride": "O prefeito autorizou hoje."
            },
            headers={"Authorization": f"Bearer {token_operador}"}
        )
        assert r.status_code == 403

    def test_patch_transferencia_efetivada_bloqueia_estrutural_retorna_409(self, client, token_admin, db):
        """Se a transferência não estiver PENDENTE, não pode mudar destino, mesmo com override"""
        t_id = self._preparar_dados(client, token_admin, db)
        
        # 1. Aprova a transferência primeiro
        client.post(
            f"/transferencias/{t_id}/aprovacoes", 
            json={"decisao": "APROVADA"},
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        
        # 2. Tenta editar o destino de uma transferência já concluída
        r = client.patch(
            f"/transferencias/{t_id}", 
            json={"setorDestino": "uuid-setor-c", "overrideAdmin": True, "motivoOverride": "Mudei de ideias super tarde"},
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert r.status_code == 409