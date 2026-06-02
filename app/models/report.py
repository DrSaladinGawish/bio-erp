from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from app.database import Base


class ReportMetadata(Base):
    __tablename__ = "report_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    report_type = Column(String(100), nullable=False)
    format = Column(String(10), nullable=False)
    path = Column(Text, nullable=False)
    source_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
