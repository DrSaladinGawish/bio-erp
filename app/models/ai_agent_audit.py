from datetime import timezone, datetime
from sqlalchemy import Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AiAgentAudit(Base):
    __tablename__ = "ai_agent_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="gap_scanner / health_monitor / bilingual_chat / auto_remediation / protocol_enforcer")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="SCAN / REMEDIATE / ALERT / CHAT / ENFORCE")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="pending / running / success / failed / rejected")
    trigger: Mapped[str] = mapped_column(String(50), nullable=True, comment="manual / schedule / webhook / chat")
    input_data: Mapped[str] = mapped_column(Text, nullable=True, comment="JSON of request input")
    output_data: Mapped[str] = mapped_column(Text, nullable=True, comment="JSON of result output")
    severity: Mapped[str] = mapped_column(String(10), nullable=True, comment="P0 / P1 / P2 / P3")
    target_organ: Mapped[str] = mapped_column(String(100), nullable=True, comment="Affected ERP organ")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    execution_ms: Mapped[float] = mapped_column(Float, nullable=True, comment="Duration in milliseconds")
    approved_by: Mapped[int] = mapped_column(Integer, nullable=True, comment="User ID who approved remediation")
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    branch_id: Mapped[int] = mapped_column(Integer, default=1)
