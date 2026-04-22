# tests/test_middleware.py
"""
Testes do CorrelationIDMiddleware.
Garante que X-Correlation-ID é ecoado em todas as respostas
e gerado automaticamente quando ausente.
"""
import uuid


class TestCorrelationIDMiddleware:
    def test_ecoa_correlation_id_enviado(self, client):
        cid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        r = client.get("/", headers={"X-Correlation-ID": cid})
        assert r.headers.get("X-Correlation-ID") == cid

    def test_gera_correlation_id_quando_ausente(self, client):
        r = client.get("/")
        cid = r.headers.get("X-Correlation-ID")
        assert cid is not None
        # deve ser UUID válido
        uuid.UUID(cid)

    def test_correlation_id_presente_em_rota_protegida(self, client, h_admin, patrimonio_ativo):
        cid = "12345678-0000-0000-0000-000000000000"
        headers = {**h_admin, "X-Correlation-ID": cid}
        r = client.get(f"/patrimonios/{patrimonio_ativo.numero}", headers=headers)
        assert r.headers.get("X-Correlation-ID") == cid

    def test_correlation_id_presente_em_erro_404(self, client, h_admin):
        cid = "99999999-0000-0000-0000-000000000000"
        headers = {**h_admin, "X-Correlation-ID": cid}
        r = client.get("/patrimonios/INEXISTENTE", headers=headers)
        assert r.headers.get("X-Correlation-ID") == cid

    def test_correlation_id_presente_em_erro_401(self, client):
        cid = "deadbeef-0000-0000-0000-000000000000"
        r = client.get("/patrimonios/qualquer", headers={"X-Correlation-ID": cid})
        assert r.headers.get("X-Correlation-ID") == cid