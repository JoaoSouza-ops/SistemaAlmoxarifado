# tests/test_auth.py
"""
Testes do módulo de autenticação.
Cobre: login feliz, credencial errada, usuário inativo,
       escopos no token, escopos_override, token expirado/inválido.
"""
import pytest
from jose import jwt
from app.auth import SECRET_KEY, ALGORITHM, ESCOPOS_POR_CARGO


class TestLogin:
    def test_login_admin_retorna_token_e_escopos(self, client, usuario_admin):
        r = client.post("/auth/login", data={
            "username": "admin@sgm.gov.br",
            "password": "senha_segura_123",
        })
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert set(body["escopos"]) == set(ESCOPOS_POR_CARGO["ADMIN"])

    def test_token_contem_sub_cargo_e_escopos(self, client, usuario_admin):
        r = client.post("/auth/login", data={
            "username": "admin@sgm.gov.br",
            "password": "senha_segura_123",
        })
        payload = jwt.decode(r.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "admin@sgm.gov.br"
        assert payload["cargo"] == "ADMIN"
        assert "patrimonio:write" in payload["escopos"]
        assert "admin:override" in payload["escopos"]

    def test_login_senha_errada_retorna_401(self, client, usuario_admin):
        r = client.post("/auth/login", data={
            "username": "admin@sgm.gov.br",
            "password": "senha_errada",
        })
        assert r.status_code == 401

    def test_login_email_inexistente_retorna_401(self, client):
        r = client.post("/auth/login", data={
            "username": "naoexiste@sgm.gov.br",
            "password": "qualquer",
        })
        assert r.status_code == 401

    def test_login_usuario_inativo_retorna_403(self, client, usuario_inativo):
        r = client.post("/auth/login", data={
            "username": "inativo@sgm.gov.br",
            "password": "qualquer123",
        })
        assert r.status_code == 403

    def test_login_com_escopos_override(self, client, db):
        import json
        from app.models.usuario import UsuarioModel
        from app.auth import hash_senha
        escopos_restritos = ["patrimonio:read"]
        u = UsuarioModel(
            nome_completo="Restrito",
            email="restrito@sgm.gov.br",
            senha_hash=hash_senha("senha123"),
            cargo="ADMIN",
            ativo=True,
            escopos_override=json.dumps(escopos_restritos),
        )
        db.add(u)
        db.commit()

        r = client.post("/auth/login", data={
            "username": "restrito@sgm.gov.br",
            "password": "senha123",
        })
        assert r.status_code == 200
        # escopos_override prevalece sobre o padrão do cargo ADMIN
        assert r.json()["escopos"] == escopos_restritos


class TestProtecaoEndpoints:
    def test_sem_token_retorna_401(self, client):
        r = client.get("/patrimonios/2026-000001")
        assert r.status_code == 401

    def test_token_invalido_retorna_401(self, client):
        r = client.get(
            "/patrimonios/2026-000001",
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert r.status_code == 401

    def test_escopo_insuficiente_retorna_403(self, client, patrimonio_ativo, h_visualizador):
        # visualizador tem patrimonio:read mas não patrimonio:write — não pode fazer baixa
        r = client.post(
            f"/patrimonios/{patrimonio_ativo.numero}/baixas",
            json={"justificativa": "Equipamento com defeito irreparável"},
            headers=h_visualizador,
        )
        assert r.status_code == 403