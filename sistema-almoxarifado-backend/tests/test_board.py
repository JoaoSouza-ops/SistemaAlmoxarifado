# tests/test_board.py
"""
Testes do board de anotações operacionais.
Cobre: criação com categorias válidas, listagem, validações.
"""
import pytest


class TestCriarNota:
    def test_criar_nota_aviso(self, client, h_admin):
        r = client.post("/board/notas", json={
            "titulo": "Sistema em manutenção programada",
            "descricao": "Manutenção de rotina às 22h",
            "categoria": "AVISO",
            "fixado": True,
        }, headers=h_admin)
        assert r.status_code == 201
        body = r.json()
        assert body["titulo"] == "Sistema em manutenção programada"
        assert body["categoria"] == "AVISO"
        assert body["fixado"] is True

    def test_criar_nota_pendencia(self, client, h_operador):
        r = client.post("/board/notas", json={
            "titulo": "Inventário pendente setor TI",
            "categoria": "PENDENCIA",
        }, headers=h_operador)
        assert r.status_code == 201
        assert r.json()["categoria"] == "PENDENCIA"

    def test_criar_nota_manutencao(self, client, h_admin):
        r = client.post("/board/notas", json={
            "titulo": "Reparo no elevador de carga",
            "categoria": "MANUTENCAO",
        }, headers=h_admin)
        assert r.status_code == 201

    def test_categoria_invalida_retorna_422(self, client, h_admin):
        r = client.post("/board/notas", json={
            "titulo": "Nota inválida",
            "categoria": "URGENTE",  # não existe no enum
        }, headers=h_admin)
        assert r.status_code == 422

    def test_titulo_acima_de_100_chars_retorna_422(self, client, h_admin):
        r = client.post("/board/notas", json={
            "titulo": "A" * 101,
            "categoria": "AVISO",
        }, headers=h_admin)
        assert r.status_code == 422

    def test_nota_sem_titulo_retorna_422(self, client, h_admin):
        r = client.post("/board/notas", json={
            "categoria": "AVISO",
        }, headers=h_admin)
        assert r.status_code == 422

    def test_fixado_default_e_false(self, client, h_admin):
        r = client.post("/board/notas", json={
            "titulo": "Nota sem fixado",
            "categoria": "AVISO",
        }, headers=h_admin)
        assert r.status_code == 201
        assert r.json()["fixado"] is False


class TestListarNotas:
    def test_listar_retorna_lista(self, client, h_visualizador):
        r = client.get("/board/notas", headers=h_visualizador)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_nota_criada_aparece_na_listagem(self, client, h_admin, h_visualizador):
        client.post("/board/notas", json={
            "titulo": "Nota para listar",
            "categoria": "AVISO",
        }, headers=h_admin)
        r = client.get("/board/notas", headers=h_visualizador)
        titulos = [n["titulo"] for n in r.json()]
        assert "Nota para listar" in titulos