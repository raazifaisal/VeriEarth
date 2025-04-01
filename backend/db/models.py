from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True, unique=True)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
