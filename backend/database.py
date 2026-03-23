from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from credentials import password, user

DATABASE_URL = f"{user}://postgres:{password}@localhost:5432/ai_app"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
