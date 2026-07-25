import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

# Admin engine — tables banane, seed karne ke liye
admin_engine = create_engine(
    os.getenv("DATABASE_URL"),
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Read-only engine — agent isi se query chalayega
readonly_engine = create_engine(
    os.getenv("READONLY_DATABASE_URL"),
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Sessions — DB ke saath baat karne ka handle
AdminSession = sessionmaker(bind=admin_engine)
ReadonlySession = sessionmaker(bind=readonly_engine)


class Base(DeclarativeBase):
    """Sabhi models (tables) isi se inherit karenge."""
    pass