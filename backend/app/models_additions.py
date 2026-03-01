from sqlalchemy import Column, String, Text, Boolean, DateTime
from .database import Base
from datetime import datetime

class AppSettings(Base):
    __tablename__ = 'app_settings'
    
    key = Column(String, primary_key=True)
    value = Column(Text)  # Fernet-encrypted for sensitive values
    is_sensitive = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings(key='{self.key}', is_sensitive={self.is_sensitive})>"
