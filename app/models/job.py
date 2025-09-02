# ===================================
# Fichier: app/models/job.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False, index=True)  # Type de job
    payload = Column(JSON, nullable=True)  # Données du job
    status = Column(String, default=JobStatus.PENDING, nullable=False, index=True)
    
    # Planification
    run_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Tentatives
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Résultats
    result = Column(JSON, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<JobQueue(id={self.id}, kind='{self.kind}', status='{self.status}')>"

    def is_ready(self) -> bool:
        """Vérifier si le job est prêt à être exécuté"""
        return (self.status == JobStatus.PENDING and 
                self.run_at <= datetime.utcnow() and
                self.attempts < self.max_attempts)

    def mark_running(self):
        """Marquer le job comme en cours d'exécution"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result=None):
        """Marquer le job comme terminé"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result

    def mark_failed(self, error: str):
        """Marquer le job comme échoué"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.last_error = error
        self.attempts += 1