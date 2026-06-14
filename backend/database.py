from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from credentials import password, user

DATABASE_URL = f"{user}://postgres:{password}@localhost:5432/ai_app"

engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=50, pool_timeout=60, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
