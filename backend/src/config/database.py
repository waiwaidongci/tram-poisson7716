from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from src.config.settings import DB_URL

class Base(DeclarativeBase):
    pass

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=240)
Session = sessionmaker(engine, expire_on_commit=False)


def connection():
    with Session() as db:
        yield db
