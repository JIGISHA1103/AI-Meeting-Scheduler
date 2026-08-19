import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# PostgreSQL Configuration
# --------------------------------------------------

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if not POSTGRES_PASSWORD:
    raise Exception(
        "POSTGRES_PASSWORD not found in .env file"
    )


DATABASE_URL = (
    f"postgresql+psycopg2://postgres:{POSTGRES_PASSWORD}"
    "@localhost:5432/meeting_ai"
)


# --------------------------------------------------
# Database Engine
# --------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    echo=False
)


# --------------------------------------------------
# Database Session
# --------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# --------------------------------------------------
# Base Class for Database Models
# --------------------------------------------------

Base = declarative_base()


# --------------------------------------------------
# Database Dependency
# --------------------------------------------------

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()