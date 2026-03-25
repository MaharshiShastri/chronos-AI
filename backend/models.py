from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
from zoneinfo import ZoneInfo

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index = True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    timezone_name = Column(String, default="UTC")

    conversations = relationship("Conversation", back_populates="owner")

    def get_local_time(self, dt):
        try:
            user_tz = ZoneInfo(self.timezone_name)
            return dt.astimezone(user_tz)
        
        except Exception:
            return dt

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    title = Column(String, default="New Session")

    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key= True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String) #"user" or "llm"
    content = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")
