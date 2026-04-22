# tests/conftest.py
"""
Fixtures compartilhadas por toda a suíte.

Estratégia de banco:
  - SQLite in-memory por sessão de teste (:memory:)
  - Cada test function recebe um client com banco limpo via rollback
  - Tokens pré-gerados para os 3 perfis: admin, operador, visualizador
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.usuario import UsuarioModel
from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.models.board import NotaBoardModel
from app.auth import hash_senha, criar_token_acesso, ESCOPOS_POR_CARGO

# ── Banco de testes em memória ────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # mesma conexão em todos os threads — necessário para SQLite in-memory
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def criar_tabelas():
    """Cria todas as tabelas uma vez por sessão de testes."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture()
def db():
    """
    Sessão de banco isolada por teste.
    Usa transação aninhada + rollback para garantir banco limpo após cada teste.
    """
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """
    TestClient com override de get_db apontando para o banco de teste isolado.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # rollback já tratado pela fixture db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tokens por perfil ─────────────────────────────────────────────────────────

@pytest.fixture()
def token_admin():
    return criar_token_acesso({
        "sub": "admin@sgm.gov.br",
        "cargo": "ADMIN",
        "escopos": ESCOPOS_POR_CARGO["ADMIN"],
    })


@pytest.fixture()
def token_operador():
    return criar_token_acesso({
        "sub": "operador@sgm.gov.br",
        "cargo": "OPERADOR",
        "escopos": ESCOPOS_POR_CARGO["OPERADOR"],
    })


@pytest.fixture()
def token_visualizador():
    return criar_token_acesso({
        "sub": "visualizador@sgm.gov.br",
        "cargo": "VISUALIZADOR",
        "escopos": ESCOPOS_POR_CARGO["VISUALIZADOR"],
    })


# ── Headers prontos ───────────────────────────────────────────────────────────

@pytest.fixture()
def h_admin(token_admin):
    return {
        "Authorization": f"Bearer {token_admin}",
        "X-Correlation-ID": "00000000-0000-0000-0000-000000000001",
    }


@pytest.fixture()
def h_operador(token_operador):
    return {
        "Authorization": f"Bearer {token_operador}",
        "X-Correlation-ID": "00000000-0000-0000-0000-000000000002",
    }


@pytest.fixture()
def h_visualizador(token_visualizador):
    return {
        "Authorization": f"Bearer {token_visualizador}",
        "X-Correlation-ID": "00000000-0000-0000-0000-000000000003",
    }


# ── Fixtures de dados reutilizáveis ───────────────────────────────────────────

@pytest.fixture()
def patrimonio_ativo(db):
    """Insere e retorna um patrimônio com status ATIVO."""
    p = PatrimonioModel(
        numero="2026-000001",
        descricao="Notebook Dell Latitude",
        status="ATIVO",
        setor_atual="SETOR-TI",
    )
    db.add(p)
    db.add(HistoricoModel(
        patrimonio_numero="2026-000001",
        acao="CADASTRO_INICIAL",
        destino="SETOR-TI",
    ))
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def patrimonio_baixado(db):
    """Insere e retorna um patrimônio já baixado."""
    p = PatrimonioModel(
        numero="2026-000099",
        descricao="Monitor Samsung antigo",
        status="BAIXADO",
        setor_atual="SETOR-ARQUIVO",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def patrimonio_pendente(db):
    """Insere patrimônio com transferência pendente e retorna (patrimônio, transferência)."""
    p = PatrimonioModel(
        numero="2026-000002",
        descricao="Impressora HP",
        status="TRANSFERENCIA_PENDENTE",
        setor_atual="SETOR-RH",
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    t = TransferenciaModel(
        patrimonio_numero=p.numero,
        setor_origem="SETOR-RH",
        setor_destino="SETOR-FINANCEIRO",
        responsavel_recebimento="Maria Silva",
        justificativa="Necessidade operacional do setor financeiro",
        status="PENDENTE",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return p, t


@pytest.fixture()
def usuario_admin(db):
    """Insere usuário admin no banco (para testes de login)."""
    u = UsuarioModel(
        nome_completo="Admin Teste",
        email="admin@sgm.gov.br",
        senha_hash=hash_senha("senha_segura_123"),
        cargo="ADMIN",
        ativo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def usuario_inativo(db):
    u = UsuarioModel(
        nome_completo="Usuário Inativo",
        email="inativo@sgm.gov.br",
        senha_hash=hash_senha("qualquer123"),
        cargo="OPERADOR",
        ativo=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u