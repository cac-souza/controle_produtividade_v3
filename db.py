# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos import Base

# URL do banco - mesma que está no alembic.ini
DATABASE_URL = "sqlite:///./controle_produtividade.db"

# Cria o engine
# 'check_same_thread=False' é necessário para SQLite com múltiplas threads (ex.: no Streamlit ou FastAPI)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Fábrica de sessões
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db():
    """Cria as tabelas no banco caso não existam."""
    Base.metadata.create_all(bind=engine)
