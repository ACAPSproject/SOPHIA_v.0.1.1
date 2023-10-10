from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

from infrastructure.config import POSTGRES_DB_URL

engine = create_engine(
    POSTGRES_DB_URL,
    echo=True,
)

Session = sessionmaker(bind=engine, autoflush=True)
Base = declarative_base()


Session = scoped_session(sessionmaker(expire_on_commit=False, bind=engine, autoflush=True))
