import os
from logging.config import fileConfig
from dotenv import load_dotenv
from urllib.parse import quote_plus

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Charger les variables d'environnement
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Créer l'URL de la base de données avec encodage sécurisé
username = "postgres"
password = quote_plus("Digit@2")  # Encode automatiquement les caractères spéciaux
host = "localhost"
port = "5432"
database = "maef_db"

database_url = f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"
# On ne définit plus dans config pour éviter l'interpolation
# config.set_main_option('sqlalchemy.url', database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# IMPORTANT: Importez vos modèles ici
try:
    # Remplacez par le chemin vers vos modèles
    # Par exemple, si vos modèles sont dans app/models/
    from app.models import Base  # ou wherever your models are
    target_metadata = Base.metadata
except ImportError:
    # Si vous n'avez pas encore de modèles, laissez None
    target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Utiliser directement notre URL au lieu de la récupérer du config
    context.configure(
        url=database_url,
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
    # Créer la configuration manuellement pour éviter les problèmes d'interpolation
    configuration = {}
    configuration['sqlalchemy.url'] = database_url
    
    connectable = engine_from_config(
        configuration,
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