from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    total_pages = Column(Integer, default=0)
    contract_type = Column(String(50), default="UNCLASSIFIED") # NDA, MSA, SAAS, EMPLOYMENT
    status = Column(String(30), default="PENDING") # PENDING, PROCESSING, READY, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chunks = relationship("ContractChunk", back_populates="contract", cascade="all, delete-orphan")
    audits = relationship("AuditReport", back_populates="contract", cascade="all, delete-orphan")

class ContractChunk(Base):
    __tablename__ = "contract_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contract_id = Column(String(36), ForeignKey("contracts.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    parent_id = Column(String(36), nullable=True) # ID of enclosing parent section
    is_parent = Column(Boolean, default=False)
    qdrant_point_id = Column(String(36), nullable=True)
    metadata_json = Column(JSON, default=dict)

    contract = relationship("Contract", back_populates="chunks")

class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    rules_json = Column(JSON, nullable=False) # List of audit criteria rules
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    audits = relationship("AuditReport", back_populates="playbook")

class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contract_id = Column(String(36), ForeignKey("contracts.id", ondelete="CASCADE"), index=True, nullable=False)
    playbook_id = Column(String(36), ForeignKey("playbooks.id"), nullable=True)
    overall_risk_score = Column(Float, default=0.0) # 0.0 to 100.0
    risk_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    executive_summary = Column(Text, nullable=True)
    status = Column(String(30), default="IN_PROGRESS") # IN_PROGRESS, COMPLETED, FAILED
    latency_ms = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    contract = relationship("Contract", back_populates="audits")
    playbook = relationship("Playbook", back_populates="audits")
    findings = relationship("RiskFinding", back_populates="audit", cascade="all, delete-orphan")

class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    audit_id = Column(String(36), ForeignKey("audit_reports.id", ondelete="CASCADE"), index=True, nullable=False)
    clause_category = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False) # CRITICAL, HIGH, MEDIUM, LOW, ACCEPTABLE
    original_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    section_reference = Column(String(100), nullable=True)
    playbook_rule = Column(Text, nullable=True)
    deviation_explanation = Column(Text, nullable=True)
    proposed_redline = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    confidence_score = Column(Float, default=1.0)

    audit = relationship("AuditReport", back_populates="findings")

