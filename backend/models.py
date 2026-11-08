from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from datetime import datetime
from .database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), default="Anonymous")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="Under Review")

class ComparisonReport(Base):
    __tablename__ = "comparison_reports"

    id = Column(Integer, primary_key=True, index=True)
    doc_a_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    doc_b_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    doc_a_title = Column(String(255))
    doc_b_title = Column(String(255))
    overall_similarity = Column(Float, default=0.0)
    exact_similarity = Column(Float, default=0.0)
    semantic_similarity = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)
    status = Column(String(50), default="Pending Review")
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    department = Column(String(255), default="General Studies")
    evaluator_1_verdict = Column(String(50), default="Pending")
    evaluator_1_notes = Column(Text, default="")
    evaluator_2_verdict = Column(String(50), default="Pending")
    evaluator_2_notes = Column(Text, default="")
    hod_verdict = Column(String(50), default="Pending")
    hod_notes = Column(Text, default="")
    workflow_stage = Column(String(50), default="Evaluator 1")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String(10), default="✓")
    color = Column(String(50), default="")
    action = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    actor = Column(String(255), default="System")
    created_at = Column(DateTime, default=datetime.utcnow)

class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    department = Column(String(255), default="Academic Integrity")
    role = Column(String(100), default="Lead Reviewer")
    monthly_scans = Column(Integer, default=0)
    quota = Column(Integer, default=4350)
    color = Column(String(50), default="var(--green)")
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    password = Column(String(255), default="admin.123")

class SystemPolicy(Base):
    __tablename__ = "system_policies"

    id = Column(Integer, primary_key=True, index=True)
    overlap_threshold = Column(Float, default=25.0)
    paraphrase_threshold = Column(Float, default=82.0)
    cross_language = Column(Integer, default=1)
    ai_signal = Column(Integer, default=1)
    ignore_bibliography = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), default="")
    status = Column(String(50), default="active")
    department = Column(String(255), default="General Studies")
    created_at = Column(DateTime, default=datetime.utcnow)

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    otp = Column(String(10), nullable=False)
    role = Column(String(50), default="user")
    purpose = Column(String(50), default="login")
    is_verified = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

