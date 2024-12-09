import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

DATABASE_URL = os.getenv('DATABASE_URL')
DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA', 'meal')

#engine = create_engine(DATABASE_URL)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20, #10           
    max_overflow=40, #20        
    pool_timeout=60, #30         
    pool_recycle=1800
)

@event.listens_for(engine.sync_engine, 'connect')
def set_search_path(dbapi_connection, connection_record):
    existing_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    cursor = dbapi_connection.cursor()
    cursor.execute(f'SET search_path TO {DATABASE_SCHEMA}')
    cursor.close()
    dbapi_connection.autocommit = existing_autocommit

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with SessionLocal() as session:
        yield session