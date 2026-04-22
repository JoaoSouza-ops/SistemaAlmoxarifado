# tests/test_patrimonio.py
"""
Testes de patrimônios.
Cobre: cadastro, busca, baixa, importação assíncrona,
       listagem paginada por setor, relatório PDF, erros RFC 7807.
"""
import io
import pytest


class TestCadastroPatrimonio:
    def test_cadastro_cria_patrimonio_e_historico(self, client, h_admin, db):
        from app.models.patrimonio import PatrimonioModel, HistoricoModel
        r = client.post("/patrimonios/", json={
            "numero": "2026-999001",
            "descricao": "Cadeira ergonômica",
            "setor_atual": "SETOR-RH",
        }, headers=h_admin)
        assert r.status_code == 201
        body = r.json()
        assert body["numero"] == "2026-999001"
        assert body["status"] == "ATIVO"
        # confirma que trilha de auditoria foi criada
        historico = db.query(HistoricoModel).filter(
            HistoricoModel.patrimonio_numero == "2026-999001"
        ).first()
        assert historico is not None
        assert historico.acao == "CADASTRO_INICIAL"

    def test_cadastro_duplicado_retorna_409_problem_json(self, client, h_admin, patrimonio_ativo):
        r = client.post("/patrimonios/", json={
            "numero": patrimonio_ativo.numero,
            "descricao": "Duplicado",
            "setor_atual": "SETOR-X",
        }, headers=h_admin)
        assert r.status_code == 409
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["status"] == 409
        assert "type" in body
        assert "title" in body

    def test_cadastro_sem_permissao_retorna_403(self, client, h_visualizador):
        r = client.post("/patrimonios/", json={
            "numero": "2026-777001",
            "descricao": "Mesa de escritório",
            "setor_atual": "SETOR-ADM",
        }, headers=h_visualizador)
        assert r.status_code == 403


class TestBuscaPatrimonio:
    def test_busca_retorna_dados_e_historico(self, client, h_visualizador, patrimonio_ativo):
        r = client.get(f"/patrimonios/{patrimonio_ativo.numero}", headers=h_visualizador)
        assert r.status_code == 200
        body = r.json()
        assert body["numero"] == patrimonio_ativo.numero
        assert body["descricao"] == patrimonio_ativo.descricao
        # campo deve ser camelCase conforme contrato v2
        assert "setorAtual" in body
        assert "historicoMovimentacoes" in body
        assert isinstance(body["historicoMovimentacoes"], list)

    def test_busca_inexistente_retorna_404_problem_json(self, client, h_visualizador):
        r = client.get("/patrimonios/NAOEXISTE-000", headers=h_visualizador)
        assert r.status_code == 404
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["status"] == 404

    def test_busca_sem_token_retorna_401(self, client):
        r = client.get("/patrimonios/2026-000001")
        assert r.status_code == 401


class TestBaixaPatrimonio:
    def test_baixa_altera_status_e_registra_historico(self, client, h_admin, patrimonio_ativo, db):
        from app.models.patrimonio import PatrimonioModel, HistoricoModel
        r = client.post(
            f"/patrimonios/{patrimonio_ativo.numero}/baixas",
            json={"justificativa": "Equipamento com defeito irreparável comprovado"},
            headers=h_admin,
        )
        assert r.status_code == 200
        # confirma status no banco
        db.refresh(patrimonio_ativo)
        assert patrimonio_ativo.status == "BAIXADO"
        # confirma trilha de auditoria
        h = db.query(HistoricoModel).filter(
            HistoricoModel.patrimonio_numero == patrimonio_ativo.numero,
            HistoricoModel.acao == "BAIXA",
        ).first()
        assert h is not None
        assert h.destino == "DESCARTE/ARQUIVO"

    def test_baixa_dupla_retorna_422_problem_json(self, client, h_admin, patrimonio_baixado):
        r = client.post(
            f"/patrimonios/{patrimonio_baixado.numero}/baixas",
            json={"justificativa": "Tentativa de baixa duplicada aqui"},
            headers=h_admin,
        )
        assert r.status_code == 422
        assert r.headers["content-type"] == "application/problem+json"

    def test_baixa_justificativa_curta_retorna_422(self, client, h_admin, patrimonio_ativo):
        r = client.post(
            f"/patrimonios/{patrimonio_ativo.numero}/baixas",
            json={"justificativa": "curta"},
            headers=h_admin,
        )
        assert r.status_code == 422

    def test_baixa_inexistente_retorna_404(self, client, h_admin):
        r = client.post(
            "/patrimonios/NAOEXISTE/baixas",
            json={"justificativa": "Justificativa suficientemente longa aqui"},
            headers=h_admin,
        )
        assert r.status_code == 404

    def test_baixa_por_operador_retorna_403(self, client, h_operador, patrimonio_ativo):
        # operador não tem escopo patrimonio:write
        r = client.post(
            f"/patrimonios/{patrimonio_ativo.numero}/baixas",
            json={"justificativa": "Operador tentando fazer baixa indevidamente"},
            headers=h_operador,
        )
        assert r.status_code == 403


class TestImportacaoAssincrona:
    def _csv_valido(self):
        conteudo = "numero,descricao,setor\n2026-100001,Mesa de reunião,SETOR-ADM\n2026-100002,Projetor Epson,SETOR-TI\n"
        return io.BytesIO(conteudo.encode())

    def test_importacao_retorna_202_e_location(self, client, h_admin):
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("inventario.csv", self._csv_valido(), "text/csv")},
            headers=h_admin,
        )
        assert r.status_code == 202
        assert "Location" in r.headers
        assert r.headers["Location"].startswith("/v1/jobs/")

    def test_location_aponta_para_job_consultavel(self, client, h_admin):
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("inventario.csv", self._csv_valido(), "text/csv")},
            headers=h_admin,
        )
        job_path = r.headers["Location"]           # /v1/jobs/{uuid}
        job_id = job_path.split("/")[-1]
        r2 = client.get(f"/jobs/{job_id}", headers=h_admin)
        assert r2.status_code == 200
        body = r2.json()
        assert body["jobId"] == job_id
        assert body["status"] in ("PENDENTE", "PROCESSANDO", "CONCLUIDO", "ERRO")

    def test_importacao_arquivo_nao_csv_retorna_400(self, client, h_admin):
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("planilha.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
            headers=h_admin,
        )
        assert r.status_code == 400
        assert r.headers["content-type"] == "application/problem+json"

    def test_importacao_sem_permissao_retorna_403(self, client, h_operador):
        r = client.post(
            "/patrimonios/importacoes",
            files={"arquivo": ("inventario.csv", self._csv_valido(), "text/csv")},
            headers=h_operador,
        )
        assert r.status_code == 403


class TestListagemPorSetor:
    def test_listagem_retorna_paginacao_meta(self, client, h_visualizador, patrimonio_ativo):
        r = client.get(
            f"/setores/{patrimonio_ativo.setor_atual}/patrimonios",
            headers=h_visualizador,
        )
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "meta" in body
        meta = body["meta"]
        assert "totalCount" in meta
        assert "currentPage" in meta
        assert meta["currentPage"] == 1

    def test_paginacao_respeita_limit(self, client, h_visualizador, db):
        # insere 5 patrimônios no mesmo setor
        for i in range(5):
            db.add(PatrimonioModel(
                numero=f"2026-PAG{i:03}",
                descricao=f"Item paginação {i}",
                status="ATIVO",
                setor_atual="SETOR-PAGINACAO",
            ))
        db.commit()
        r = client.get(
            "/setores/SETOR-PAGINACAO/patrimonios?page=1&limit=2",
            headers=h_visualizador,
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]) == 2
        assert body["meta"]["totalCount"] == 5
        assert body["meta"]["nextCursor"] is not None

    def test_setor_sem_patrimonios_retorna_lista_vazia(self, client, h_visualizador):
        r = client.get("/setores/SETOR-VAZIO/patrimonios", headers=h_visualizador)
        assert r.status_code == 200
        body = r.json()
        assert body["data"] == []
        assert body["meta"]["totalCount"] == 0

    def test_format_pdf_retorna_501(self, client, h_visualizador):
        r = client.get(
            "/setores/SETOR-X/patrimonios?format=pdf",
            headers=h_visualizador,
        )
        assert r.status_code == 501

    def test_page_invalida_retorna_422(self, client, h_visualizador):
        r = client.get(
            "/setores/SETOR-X/patrimonios?page=0",
            headers=h_visualizador,
        )
        assert r.status_code == 422

    def test_limit_acima_de_100_retorna_422(self, client, h_visualizador):
        r = client.get(
            "/setores/SETOR-X/patrimonios?limit=101",
            headers=h_visualizador,
        )
        assert r.status_code == 422


class TestRelátorioPDF:
    def test_relatorio_retorna_pdf_binario(self, client, h_visualizador, patrimonio_ativo):
        r = client.get(
            f"/patrimonios/{patrimonio_ativo.numero}/relatorio-pdf",
            headers=h_visualizador,
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_relatorio_inexistente_retorna_404(self, client, h_visualizador):
        r = client.get("/patrimonios/NAOEXISTE/relatorio-pdf", headers=h_visualizador)
        assert r.status_code == 404


# import necessário para o teste de paginação
from app.models.patrimonio import PatrimonioModel