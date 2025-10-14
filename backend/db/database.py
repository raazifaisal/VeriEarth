from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()               

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_neo4j():
    session = neo4j_driver.session()
    try:
        yield session
    finally:
        session.close()


def create_org_schema(schema_name: str):
    """Create a new PostgreSQL schema for an organization if it doesn't exist."""
    with engine.connect() as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        conn.commit()


def set_search_path(schema_name: str):
    """Set the search_path to the organization's schema for the current session."""
    @event.listens_for(SessionLocal, "after_begin")
    def _set_search_path(session, transaction, connection):
        connection.exec_driver_sql(f"SET search_path TO {schema_name}, public")
