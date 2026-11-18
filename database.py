from sqlmodel import Session, create_engine

DATABASE_URL = "postgresql://postgres:123Harry456@localhost:5432/submission_db"
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session