import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False, default=dict)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    actor_name = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    object_type = Column(String(100), nullable=False, index=True)
    object_id = Column(String(100), nullable=True)
    result = Column(String(20), nullable=False, default="success", index=True)
    reason = Column(Text, nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    object_type = Column(String(100), nullable=False, index=True)
    object_id = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=False)
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())


class ReferenceImage(Base):
    __tablename__ = "reference_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lab_id = Column(String(36), ForeignKey("labs.id"), nullable=False, index=True)
    image_url = Column(String(1000), nullable=False)
    label = Column(String(100), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    checksum = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
