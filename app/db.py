from sqlmodel import create_engine, Session
from app.core.config import settings

if settings.DB_BACKEND == "sqlite":
    connect_args = {"check_same_thread": False}
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI),
                           connect_args=connect_args)


def create_db_and_tables():
    # SQLModel.metadata.create_all(engine)
    pass


def get_session():
    with Session(engine) as session:
        yield session
