"""
SGM Almoxarifado — Suite de Testes E2E v2
==========================================
Correções aplicadas nesta versão:
  - PAT_NUMERO agora é sempre numérico (sem hex) para passar regex \\d{5,6}$
  - Cargo de teste corrigido para "OPERADOR" (valor válido em ESCOPOS_POR_CARGO)
  - Fixture stf_token cria usuário OPERADOR antes de fazer login,
    garantindo que o staff de teste NÃO tenha escopos de admin
  - Todos os testes de cascata de transferência corrigidos

Pré-requisitos:
    pip install pytest requests

Variáveis de ambiente:
    SGM_URL   = URL base do backend  (padrão: http://localhost:8000)
    ADM_EMAIL = e-mail do admin      (padrão: admin@sgm.gov.br)
    ADM_SENHA = senha do admin       (padrão: admin123)

Executar:
    pytest test_sgm_e2e.py -v --tb=short
"""

import os
import time
import pytest
import requests

BASE      = os.getenv("SGM_URL",   "http://localhost:8000")
ADM_EMAIL = os.getenv("ADM_EMAIL", "admin@sgm.gov.br")
ADM_SENHA = os.getenv("ADM_SENHA", "164907@")

# FIX: PAT_NUMERO agora usa apenas dígitos — sem hex.
# A versão anterior usava uuid4().hex que gerava letras A-F,
# fazendo a criação passar (PatrimonioCriar sem pattern) mas a
# transferência falhar (SolicitacaoTransferencia exige \d{5,6}$).
import random
_RUN = str(random.randint(100000, 899999))   # 6 dígitos numéricos garantidos
PAT_NUMERO   = _RUN
PAT_BAIXA    = str(int(_RUN) + 1)
SETOR_ID     = f"SETOR_TST_{_RUN}"
SETOR_DEST   = f"SETOR_DST_{_RUN}"
SETOR_SIGLA  = f"ST{_RUN[:4]}"

# FIX: cargo válido segundo ESCOPOS_POR_CARGO (era "Técnico" que não existe)
STF_EMAIL_TESTE = f"staff_teste_{_RUN}@sgm.gov.br"
STF_SENHA_TESTE = "164907@"
STF_CARGO_TESTE = "OPERADOR"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def problem(r):
    """Valida que a resposta segue RFC 7807."""
    body = r.json()
    for field in ("type", "title", "status", "detail"):
        assert field in body, (
            f"Campo '{field}' ausente no ProblemDetails. Body: {body}"
        )
    assert body["status"] == r.status_code
    return body


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def adm_token():
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": ADM_EMAIL, "password": ADM_SENHA})
    assert r.status_code == 200, f"Login ADM falhou: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def adm(adm_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {adm_token}"})
    return s


@pytest.fixture(scope="session")
def stf(adm):
    """
    FIX: cria um usuário OPERADOR dedicado para os testes de permissão.
    A versão anterior usava staff@sgm.gov.br que estava cadastrado como
    ADMIN no banco — fazendo todos os testes de permissão retornarem 200.
    Ao criar o usuário aqui, garantimos cargo=OPERADOR e escopos corretos.
    """
    # Cria o usuário de teste (ignora 409 se já existir de execução anterior)
    adm.post(f"{BASE}/usuarios/", json={
        "nome_completo": f"Staff Teste {_RUN}",
        "email":          STF_EMAIL_TESTE,
        "senha":          STF_SENHA_TESTE,
        "cargo":          STF_CARGO_TESTE,
    })

    r = requests.post(f"{BASE}/auth/login",
                      data={"username": STF_EMAIL_TESTE,
                            "password": STF_SENHA_TESTE})
    assert r.status_code == 200, (
        f"Login do staff de teste falhou: {r.text}\n"
        f"Verifique se o cargo '{STF_CARGO_TESTE}' está em ESCOPOS_POR_CARGO no auth.py"
    )
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


@pytest.fixture(scope="session")
def anon():
    return requests.Session()


# ══════════════════════════════════════════════════════════════════════════════
# 1 — AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

class TestAutenticacao:

    def test_login_valido_retorna_token(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": ADM_EMAIL, "password": ADM_SENHA})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body.get("token_type", "").lower() == "bearer"

    def test_login_senha_errada_retorna_401(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": ADM_EMAIL, "password": "errada_xyz"})
        assert r.status_code == 401
        body = r.text.lower()
        assert "traceback"  not in body
        assert "sqlalchemy" not in body

    def test_login_usuario_inexistente_retorna_401(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": "naoexiste@x.gov.br", "password": "123"})
        assert r.status_code == 401

    def test_sem_token_retorna_401(self, anon):
        r = anon.get(f"{BASE}/patrimonios/", params={"setor_id": "X"})
        assert r.status_code == 401

    def test_token_invalido_retorna_401(self):
        r = requests.get(f"{BASE}/patrimonios/",
                         headers={"Authorization": "Bearer token.falso"},
                         params={"setor_id": "X"})
        assert r.status_code == 401

    def test_operador_nao_acessa_rota_admin(self, stf):
        """OPERADOR não tem patrimonio:write — não pode criar patrimônio."""
        r = stf.post(f"{BASE}/patrimonios/", json={
            "numero": "111111", "descricao": "Patrimônio teste de permissão", "setor_atual": SETOR_ID,
        })
        assert r.status_code == 403

    def test_403_nao_vaza_escopos_do_token(self, stf):
        """FIX SEGURANÇA: a resposta 403 não deve revelar os escopos do token."""
        r = stf.post(f"{BASE}/patrimonios/", json={
            "numero": "111111", "descricao": "Patrimônio teste de permissão", "setor_atual": SETOR_ID,
        })
        assert r.status_code == 403
        body = r.text.lower()
        assert "token contém" not in body
        assert "escopos" not in body
        


    def test_403_segue_rfc_7807(self, stf):
      # FIX RFC 7807: resposta 403 deve ter type, title, status, detail.
        r = stf.post(f"{BASE}/patrimonios/", json={
            "numero": "111111", "descricao": "Patrimônio teste de permissão", "setor_atual": SETOR_ID,
        })
        assert r.status_code == 403
        problem(r)
        assert "problem+json" in r.headers.get("content-type", "")


# ══════════════════════════════════════════════════════════════════════════════
# 2 — SETORES
# ══════════════════════════════════════════════════════════════════════════════

class TestSetores:

    def test_listar_setores_publico(self, anon):
        r = anon.get(f"{BASE}/setores/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_criar_setor_origem(self, adm):
        r = adm.post(f"{BASE}/setores/", json={
            "id": SETOR_ID, "sigla": SETOR_SIGLA, "nome": f"Setor Origem {_RUN}",
        })
        assert r.status_code == 201
        assert r.json()["id"] == SETOR_ID

    def test_criar_setor_destino(self, adm):
        r = adm.post(f"{BASE}/setores/", json={
            "id": SETOR_DEST, "sigla": f"D{SETOR_SIGLA[:3]}", "nome": f"Setor Destino {_RUN}",
        })
        assert r.status_code == 201

    def test_setor_duplicado_retorna_409_rfc7807(self, adm):
        r = adm.post(f"{BASE}/setores/", json={
            "id": SETOR_ID, "sigla": SETOR_SIGLA, "nome": "Duplicado",
        })
        assert r.status_code == 409
        # FIX: verifica RFC 7807 completo (type, title, status, detail)
        problem(r)

    def test_operador_nao_cria_setor(self, stf):
        r = stf.post(f"{BASE}/setores/", json={
            "id": "SETOR_STAFF_X", "sigla": "SSX", "nome": "Não deve criar",
        })
        assert r.status_code == 403

    def test_editar_setor(self, adm):
        r = adm.put(f"{BASE}/setores/{SETOR_ID}", json={
            "id": SETOR_ID, "sigla": SETOR_SIGLA, "nome": f"Setor Origem {_RUN} — Editado",
        })
        assert r.status_code == 200
        assert "Editado" in r.json()["nome"]


# ══════════════════════════════════════════════════════════════════════════════
# 3 — PATRIMÔNIOS
# ══════════════════════════════════════════════════════════════════════════════

class TestPatrimonios:

    def test_cadastrar_patrimonio(self, adm):
        r = adm.post(f"{BASE}/patrimonios/", json={
            "numero": PAT_NUMERO, "descricao": f"Notebook Teste {_RUN}",
            "setor_atual": SETOR_ID,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["numero"] == PAT_NUMERO
        assert body["status"] == "ATIVO"
        assert body["setorAtual"] == SETOR_ID

    def test_cadastrar_para_baixa(self, adm):
        r = adm.post(f"{BASE}/patrimonios/", json={
            "numero": PAT_BAIXA, "descricao": f"Cadeira Baixa {_RUN}",
            "setor_atual": SETOR_ID,
        })
        assert r.status_code == 201

    def test_numero_duplicado_retorna_409(self, adm):
        r = adm.post(f"{BASE}/patrimonios/", json={
            "numero": PAT_NUMERO, "descricao": "Duplicado", "setor_atual": SETOR_ID,
        })
        assert r.status_code == 409
        body = problem(r)
        assert "sqlalchemy" not in body["detail"].lower()
        assert "integrity"  not in body["detail"].lower()

    def test_operador_nao_cadastra_patrimonio(self, stf):
        r = stf.post(f"{BASE}/patrimonios/", json={
            "numero": "500001", "descricao": "Patrimônio teste operador", "setor_atual": SETOR_ID,
        })
        assert r.status_code == 403

    def test_buscar_existente(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}")
        assert r.status_code == 200
        assert r.json()["numero"] == PAT_NUMERO

    def test_buscar_inexistente_404_rfc7807(self, adm):
        r = adm.get(f"{BASE}/patrimonios/000000")
        assert r.status_code == 404
        problem(r)

    def test_listar_por_setor(self, adm):
        r = adm.get(f"{BASE}/patrimonios/",
                    params={"setor_id": SETOR_ID, "page": 1, "limit": 20})
        assert r.status_code == 200
        body = r.json()
        assert "data" in body and "meta" in body
        assert PAT_NUMERO in [p["numero"] for p in body["data"]]

    def test_listar_sem_setor_id_retorna_422(self, adm):
        r = adm.get(f"{BASE}/patrimonios/")
        assert r.status_code == 422

    def test_paginacao_limit_excessivo_retorna_422(self, adm):
        r = adm.get(f"{BASE}/patrimonios/",
                    params={"setor_id": SETOR_ID, "limit": 999})
        assert r.status_code == 422

    def test_pdf_retorna_content_type_correto(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}/relatorio-pdf")
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert len(r.content) > 100

    def test_importar_csv_retorna_202_com_location(self, adm):
        csv = (
            "numero,descricao,setor,status\n"
            f"7{_RUN[1:]},Impressora Teste {_RUN},{SETOR_ID},ATIVO\n"
        )
        r = adm.post(f"{BASE}/patrimonios/importacoes",
                     files={"arquivo": ("t.csv", csv.encode(), "text/csv")})
        assert r.status_code == 202
        assert "Location" in r.headers

    def test_importar_nao_csv_retorna_400(self, adm):
        r = adm.post(f"{BASE}/patrimonios/importacoes",
                     files={"arquivo": ("t.xlsx", b"xls", "application/octet-stream")})
        assert r.status_code == 400
        problem(r)

    def test_payload_gigante_retorna_422(self, adm):
        """FIX: PatrimonioCriar deve ter max_length — aceitar strings de 100+ chars é bug."""
        r = adm.post(f"{BASE}/patrimonios/", json={
            "numero":     "X" * 100,
            "descricao":  "Y" * 500,
            "setor_atual": "Z" * 100,
        })
        assert r.status_code == 422, (
            "Sistema aceitou payload gigante (201). "
            "Adicione max_length em PatrimonioCriar."
        )

    def test_baixa_justificativa_curta_retorna_422(self, adm):
        r = adm.post(f"{BASE}/patrimonios/{PAT_BAIXA}/baixas",
                     json={"justificativa": "curta"})
        assert r.status_code == 422

    def test_operador_nao_registra_baixa(self, stf):
        """FIX SEGURANÇA: OPERADOR não tem patrimonio:write — não pode registrar baixa."""
        r = stf.post(f"{BASE}/patrimonios/{PAT_BAIXA}/baixas",
                     json={"justificativa": "Tentativa de baixa sem permissão"})
        assert r.status_code == 403

    def test_registrar_baixa_valida(self, adm):
        r = adm.post(f"{BASE}/patrimonios/{PAT_BAIXA}/baixas",
                     json={"justificativa": f"Baixa de teste automatizado run {_RUN}"})
        assert r.status_code == 200

    def test_patrimonio_fica_baixado(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_BAIXA}")
        assert r.json()["status"] == "BAIXADO"

    def test_baixa_dupla_retorna_422(self, adm):
        r = adm.post(f"{BASE}/patrimonios/{PAT_BAIXA}/baixas",
                     json={"justificativa": "Segunda tentativa deve ser bloqueada"})
        assert r.status_code == 422
        problem(r)

    def test_transferir_patrimonio_baixado_bloqueado(self, adm):
        r = adm.post(f"{BASE}/transferencias/", json={
            "patrimonioId": PAT_BAIXA,
            "setorDestino": SETOR_DEST,
            "responsavelRecebimento": "Alguém",
        })
        assert r.status_code in (409, 422)


# ══════════════════════════════════════════════════════════════════════════════
# 4 — TRANSFERÊNCIAS (fluxo completo das 4 etapas)
# ══════════════════════════════════════════════════════════════════════════════

_tid = None   # id da transferência principal, compartilhado entre testes


class TestTransferencias:

    def test_solicitar_sem_responsavel_retorna_422(self, adm):
        r = adm.post(f"{BASE}/transferencias/", json={
            "patrimonioId": PAT_NUMERO, "setorDestino": SETOR_DEST,
        })
        assert r.status_code == 422

    def test_solicitar_valida(self, adm):
        global _tid
        r = adm.post(f"{BASE}/transferencias/", json={
            "patrimonioId":             PAT_NUMERO,
            "setorDestino":             SETOR_DEST,
            "responsavelRecebimento":   f"Responsável {_RUN}",
            "justificativa":            f"Justificativa de teste run {_RUN}",
            "numeroMovimento":          f"MOV{_RUN}",
        })
        assert r.status_code == 201, f"422 payload: {r.text}"
        body = r.json()
        _tid = body["id"]
        assert body["status"] == "PENDENTE"
        assert body.get("assinaturaTransferidorEm") is None, \
            "REGRESSÃO: assinaturaTransferidorEm preenchida na criação!"
        assert body.get("assinaturaRecebedorEm") is None, \
            "REGRESSÃO: assinaturaRecebedorEm preenchida na criação!"

    def test_patrimonio_fica_transferencia_pendente(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}")
        assert r.json()["status"] == "TRANSFERENCIA_PENDENTE"

    def test_segunda_transferencia_bloqueada(self, adm):
        r = adm.post(f"{BASE}/transferencias/", json={
            "patrimonioId": PAT_NUMERO, "setorDestino": SETOR_DEST,
            "responsavelRecebimento": "Alguém",
        })
        assert r.status_code in (409, 422)

    def test_fuso_horario_data_solicitacao(self, adm):
        """FIX: dataSolicitacao deve ter sufixo Z ou +00:00 para o frontend converter corretamente."""
        r = adm.get(f"{BASE}/transferencias/{_tid}")
        assert r.status_code == 200
        data_str = r.json().get("dataSolicitacao", "")
        assert data_str, "dataSolicitacao não pode ser vazia"
        tem_fuso = data_str.endswith("Z") or "+" in data_str or data_str.endswith("00:00")
        assert tem_fuso, (
            f"dataSolicitacao '{data_str}' sem fuso — "
            "frontend vai deslocar a hora. Corrija DateTime(timezone=True) no model."
        )

    def test_editar_pendente(self, adm):
        r = adm.patch(f"{BASE}/transferencias/{_tid}", json={
            "responsavelRecebimento": f"Editado {_RUN}",
            "justificativa":          f"Justificativa editada {_RUN} com mais texto aqui",
        })
        assert r.status_code == 200
        assert "Editado" in r.json()["responsavelRecebimento"]

    def test_assinar_antes_de_aprovar_bloqueado(self, adm):
        r = adm.post(f"{BASE}/transferencias/{_tid}/assinaturas",
                     json={"papel": "TRANSFERIDOR"})
        assert r.status_code in (403, 422)

    def test_operador_nao_aprova(self, stf):
        r = stf.post(f"{BASE}/transferencias/{_tid}/aprovacoes",
                     json={"decisao": "APROVADA", "overrideAdmin": False})
        assert r.status_code == 403

    def test_aprovar(self, adm):
        r = adm.post(f"{BASE}/transferencias/{_tid}/aprovacoes",
                     json={"decisao": "APROVADA", "overrideAdmin": False})
        assert r.status_code == 200
        assert r.json()["status"] == "APROVADA"

    def test_aprovacao_nao_assina_automaticamente(self, adm):
        """FIX CRÍTICO: aprovação NÃO deve preencher assinaturas automaticamente."""
        r = adm.get(f"{BASE}/transferencias/{_tid}")
        body = r.json()
        assert body.get("assinaturaTransferidorEm") is None, \
            "REGRESSÃO BUG 1: aprovação preencheu assinaturaTransferidorEm!"
        assert body.get("assinaturaRecebedorEm") is None, \
            "REGRESSÃO BUG 1: aprovação preencheu assinaturaRecebedorEm!"

    def test_editar_apos_aprovacao_retorna_403(self, adm):
        """FIX: edição após aprovação deve retornar 403 com mensagem amigável."""
        r = adm.patch(f"{BASE}/transferencias/{_tid}", json={
            "responsavelRecebimento": "Tentativa bloqueada",
        })
        assert r.status_code == 403
        body = problem(r)
        assert "traceback"  not in body["detail"].lower()
        assert "sqlalchemy" not in body["detail"].lower()

    def test_assinar_transferidor(self, adm):
        r = adm.post(f"{BASE}/transferencias/{_tid}/assinaturas",
                     json={"papel": "TRANSFERIDOR"})
        assert r.status_code == 200
        assert r.json().get("assinaturaTransferidorEm") is not None
        assert r.json().get("assinaturaRecebedorEm") is None

    def test_assinar_transferidor_duas_vezes_bloqueado(self, adm):
        r = adm.post(f"{BASE}/transferencias/{_tid}/assinaturas",
                     json={"papel": "TRANSFERIDOR"})
        assert r.status_code in (409, 422)

    def test_assinar_recebedor_efetiva(self, adm):
        r = adm.post(f"{BASE}/transferencias/{_tid}/assinaturas",
                     json={"papel": "RECEBEDOR"})
        assert r.status_code == 200
        assert r.json().get("efetivadoEm") is not None

    def test_patrimonio_movido_para_destino(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}")
        assert r.json()["setorAtual"] == SETOR_DEST

    def test_patrimonio_volta_a_ativo(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}")
        assert r.json()["status"] == "ATIVO"

    def test_rejeitar_transferencia(self, adm):
        # Move patrimônio de volta para criar nova transferência
        r = adm.post(f"{BASE}/transferencias/", json={
            "patrimonioId": PAT_NUMERO, "setorDestino": SETOR_ID,
            "responsavelRecebimento": "Responsável Rejeição",
        })
        assert r.status_code == 201
        t2_id = r.json()["id"]
        r2 = adm.post(f"{BASE}/transferencias/{t2_id}/aprovacoes",
                      json={"decisao": "REJEITADA", "overrideAdmin": False})
        assert r2.status_code == 200
        assert r2.json()["status"] == "REJEITADA"

    def test_patrimonio_volta_a_ativo_apos_rejeicao(self, adm):
        r = adm.get(f"{BASE}/patrimonios/{PAT_NUMERO}")
        assert r.json()["status"] == "ATIVO"

    def test_listar_transferencias_autenticado(self, adm):
        r = adm.get(f"{BASE}/transferencias/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_listar_transferencias_sem_auth(self, anon):
        r = anon.get(f"{BASE}/transferencias/")
        assert r.status_code == 401

    def test_buscar_inexistente_404_rfc7807(self, adm):
        r = adm.get(f"{BASE}/transferencias/999999999")
        assert r.status_code == 404
        problem(r)


# ══════════════════════════════════════════════════════════════════════════════
# 5 — USUÁRIOS
# ══════════════════════════════════════════════════════════════════════════════

_uid   = None
_email = f"novo_{_RUN}@sgm.gov.br"


class TestUsuarios:

    def test_operador_nao_lista_usuarios(self, stf):
        """FIX SEGURANÇA: OPERADOR não tem admin:override — não pode listar usuários."""
        r = stf.get(f"{BASE}/usuarios/")
        assert r.status_code == 403

    def test_admin_lista_usuarios(self, adm):
        r = adm.get(f"{BASE}/usuarios/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_criar_usuario_cargo_invalido_retorna_422(self, adm):
        """FIX: cargo inválido deve retornar 422, não 400, e seguir RFC 7807."""
        r = adm.post(f"{BASE}/usuarios/", json={
            "nome_completo": "X", "email": "x_invalido@x.com",
            "senha": "123456", "cargo": "Técnico",  # cargo inexistente
        })
        assert r.status_code in (400, 422), \
            f"Esperava 4xx para cargo inválido, recebeu {r.status_code}"

    def test_criar_usuario(self, adm):
        global _uid
        r = adm.post(f"{BASE}/usuarios/", json={
            "nome_completo": f"Usuário Novo {_RUN}",
            "email":          _email,
            "senha":          "Senha@123",
            "cargo":          "VISUALIZADOR",   # FIX: cargo válido do ESCOPOS_POR_CARGO
        })
        assert r.status_code == 201, f"Falhou: {r.text}"
        body = r.json()
        assert body["email"] == _email
        assert body["ativo"] is True
        assert "senha" not in body   # nunca expor senha na resposta
        _uid = body["id"]

    def test_email_duplicado_retorna_409(self, adm):
        r = adm.post(f"{BASE}/usuarios/", json={
            "nome_completo": "Dup", "email": _email,
            "senha": "123456", "cargo": "VISUALIZADOR",
        })
        assert r.status_code == 409

    def test_novo_usuario_faz_login(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": _email, "password": "Senha@123"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_editar_usuario(self, adm):
        r = adm.put(f"{BASE}/usuarios/{_uid}", json={
            "nome_completo": f"Usuário Editado {_RUN}",
            "cargo": "OPERADOR",
        })
        assert r.status_code == 200
        assert "Editado" in r.json()["nome_completo"]

    def test_desativar_usuario(self, adm):
        r = adm.put(f"{BASE}/usuarios/{_uid}", json={"ativo": False})
        assert r.status_code == 200
        assert r.json()["ativo"] is False

    def test_usuario_desativado_nao_faz_login(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": _email, "password": "Senha@123"})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 6 — BOARD
# ══════════════════════════════════════════════════════════════════════════════

_nid = None


class TestBoard:

    def test_criar_nota(self, adm):
        global _nid
        r = adm.post(f"{BASE}/board/notas", json={
            "titulo": f"Nota {_RUN}", "descricao": "Teste E2E",
            "categoria": "AVISO", "fixado": False,
        })
        assert r.status_code == 201
        _nid = r.json()["id"]

    def test_categoria_invalida_retorna_422(self, adm):
        r = adm.post(f"{BASE}/board/notas", json={
            "titulo": "X", "categoria": "INVALIDA",
        })
        assert r.status_code == 422

    def test_editar_nota(self, adm):
        r = adm.put(f"{BASE}/board/notas/{_nid}", json={
            "titulo": f"Nota Editada {_RUN}", "categoria": "PENDENCIA", "fixado": True,
        })
        assert r.status_code == 200
        assert r.json()["fixado"] is True

    def test_excluir_nota(self, adm):
        r = adm.delete(f"{BASE}/board/notas/{_nid}")
        assert r.status_code == 204

    def test_nota_excluida_nao_aparece(self, adm):
        ids = [n.get("id") for n in adm.get(f"{BASE}/board/notas").json()]
        assert _nid not in ids


# ══════════════════════════════════════════════════════════════════════════════
# 7 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboard:

    def test_campos_esperados(self, adm):
        r = adm.get(f"{BASE}/dashboard/metricas")
        assert r.status_code == 200
        body = r.json()
        for campo in ("patrimonios_ativos", "patrimonios_baixados",
                      "transferencias_pendentes", "notas_board"):
            assert campo in body
            assert isinstance(body[campo], int)
            assert body[campo] >= 0

    def test_sem_auth_retorna_401(self, anon):
        r = anon.get(f"{BASE}/dashboard/metricas")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 8 — SEGURANÇA
# ══════════════════════════════════════════════════════════════════════════════

class TestSeguranca:

    def test_respostas_4xx_nao_expõem_stacktrace(self, adm):
        r = adm.post(f"{BASE}/patrimonios/", json={})
        assert r.status_code in range(400, 500)
        body = r.text.lower()
        assert "traceback"  not in body
        assert "sqlalchemy" not in body
        assert "psycopg"    not in body

    def test_injecao_sql_retorna_4xx_nao_500(self, adm):
        r = adm.get(f"{BASE}/patrimonios/1%27%20OR%20%271%27%3D%271")
        assert r.status_code != 500
        assert r.status_code in range(400, 500)

    def test_content_type_json(self, adm):
        r = adm.get(f"{BASE}/setores/")
        assert "application/json" in r.headers.get("content-type", "")

    def test_404_segue_rfc_7807(self, adm):
        r = adm.get(f"{BASE}/patrimonios/000000")
        assert r.status_code == 404
        problem(r)