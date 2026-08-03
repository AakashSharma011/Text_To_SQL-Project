import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    """Sabhi models (tables) isi se inherit karenge."""
    pass


def _create_engine_for_url(db_url: str | None):
    is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    is_localhost = bool(db_url and ("localhost" in db_url or "127.0.0.1" in db_url))

    if not db_url or (is_serverless and is_localhost):
        db_url = "sqlite:////tmp/text_to_sql.db"

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )

    return create_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


# Admin engine — tables banane, seed karne ke liye
admin_db_url = os.getenv("DATABASE_URL")
readonly_db_url = os.getenv("READONLY_DATABASE_URL") or admin_db_url

admin_engine = _create_engine_for_url(admin_db_url)

# Read-only engine — agent isi se query chalayega
readonly_engine = _create_engine_for_url(readonly_db_url)

# Sessions — DB ke saath baat karne ka handle
AdminSession = sessionmaker(bind=admin_engine)
ReadonlySession = sessionmaker(bind=readonly_engine)