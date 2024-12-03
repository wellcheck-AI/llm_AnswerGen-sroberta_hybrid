import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL')
DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA', 'meal')

engine = create_engine(DATABASE_URL)

@event.listens_for(engine, 'connect')
def set_search_path(dbapi_connection, connection_record):
    existing_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    cursor = dbapi_connection.cursor()
    cursor.execute(f'SET search_path TO {DATABASE_SCHEMA}')
    cursor.close()
    dbapi_connection.autocommit = existing_autocommit

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()