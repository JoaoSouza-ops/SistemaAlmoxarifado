import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------------------
# 1. AJUSTE DO PATH (Crucial)
# Isso faz com que o script do Alembic "enxergue" a raiz do seu projeto 
# para conseguir importar a pasta onde está o seu código (ex: "app").
# -------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# -------------------------------------------------------------------
# 2. IMPORTAÇÃO DA BASE E DOS MODELOS
# -------------------------------------------------------------------
# Importe a "Base" do seu arquivo de configuração de banco de dados
from app.database import Base  # Ajuste o caminho se sua Base estiver em outro lugar

# IMPORTANTE: Importe explicitamente todos os seus modelos aqui.
# Se eles não forem importados para a memória, a Base não saberá que eles existem,
# e o Alembic vai gerar um script para deletar o banco inteiro.
from app.models.usuario import UsuarioModel
from app.models.transferencia import TransferenciaModel
from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.board import NotaBoardModel
from app.models.setor import SetorModel

# DICA: Se você tiver um arquivo __init__.py dentro da pasta models que exporta tudo,
# você poderia simplificar usando apenas: from app.models import *

# -------------------------------------------------------------------
# 3. VINCULANDO O METADATA
# -------------------------------------------------------------------
# Substitua a linha original 'target_metadata = None' por esta:
target_metadata = Base.metadata

# ... o resto do arquivo env.py (run_migrations_offline, run_migrations_online) continua igual




def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
