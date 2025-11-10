"""Database setup and session management"""
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import Optional, List
import json

from app.config import settings

Base = declarative_base()


class ConversationSession(Base):
    """Database model for conversation sessions"""
    __tablename__ = "conversations"
    
    session_id = Column(String, primary_key=True, index=True)
    messages = Column(JSON, default=list)
    triage_level = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    red_flag_detected = Column(String, nullable=True)
    
    # Relationship to temperature logs
    temperature_logs = relationship("TemperatureLog", back_populates="session", cascade="all, delete-orphan")


class TemperatureLog(Base):
    """Database model for temperature tracking"""
    __tablename__ = "temperature_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("conversations.session_id"), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    unit = Column(String, default="F")  # 'F' or 'C'
    recorded_at = Column(DateTime, default=datetime.now, index=True)
    notes = Column(Text, nullable=True)
    temperature_category = Column(String, nullable=True)  # normal, warm, fever, etc.
    
    # Relationship to conversation session
    session = relationship("ConversationSession", back_populates="temperature_logs")


class MedicationReminder(Base):
    """Database model for medication reminders"""
    __tablename__ = "medication_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("conversations.session_id"), nullable=False, index=True)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)  # e.g., "500mg"
    frequency = Column(String, nullable=False)  # e.g., "every_6_hours", "daily", "2x_daily"
    duration_days = Column(Integer, nullable=False)
    start_date = Column(DateTime, default=datetime.now)
    end_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)  # e.g., "take after food"
    is_active = Column(Integer, default=1)  # 1 = active, 0 = completed/cancelled
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship to conversation session
    session = relationship("ConversationSession")


class FeverTrendDB(Base):
    """Database model for anonymized fever trend analytics"""
    __tablename__ = "fever_trends"
    
    trend_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    city = Column(String, nullable=True)
    region = Column(String, nullable=True, index=True)
    country = Column(String, default="India")
    latitude_rounded = Column(String, nullable=True)  # Rounded for privacy
    longitude_rounded = Column(String, nullable=True)  # Rounded for privacy
    temperature_category = Column(String, nullable=True)
    probable_disease = Column(String, nullable=True, index=True)
    triage_level = Column(String, nullable=True)
    age_group = Column(String, nullable=True)
    symptoms = Column(JSON, default=list)
    fever_duration_days = Column(Integer, nullable=True)
    red_flag_detected = Column(Integer, default=0)
    emergency_referral = Column(Integer, default=0)


# Create database engine
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def save_conversation(db: Session, session_id: str, messages: list, triage_level: Optional[str] = None, 
                     summary: Optional[str] = None, red_flag: Optional[str] = None):
    """Save or update conversation session"""
    session = db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()
    
    if session:
        session.messages = messages
        session.triage_level = triage_level
        session.summary = summary
        session.red_flag_detected = red_flag
        session.updated_at = datetime.now()
    else:
        session = ConversationSession(
            session_id=session_id,
            messages=messages,
            triage_level=triage_level,
            summary=summary,
            red_flag_detected=red_flag
        )
        db.add(session)
    
    db.commit()
    return session


def get_conversation(db: Session, session_id: str) -> Optional[ConversationSession]:
    """Get conversation session by ID"""
    return db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()


def save_temperature(db: Session, session_id: str, temperature: float, unit: str = "F", notes: Optional[str] = None) -> TemperatureLog:
    """Save temperature reading to database"""
    temp_log = TemperatureLog(
        session_id=session_id,
        temperature=temperature,
        unit=unit,
        notes=notes,
        recorded_at=datetime.now()
    )
    db.add(temp_log)
    db.commit()
    db.refresh(temp_log)
    return temp_log


def get_temperature_history(db: Session, session_id: str, limit: int = 50) -> List[TemperatureLog]:
    """Get temperature history for a session"""
    try:
        return db.query(TemperatureLog).filter(
            TemperatureLog.session_id == session_id
        ).order_by(
            TemperatureLog.recorded_at.desc()
        ).limit(limit).all()
    except Exception as e:
        print(f"Error fetching temperature history: {e}")
        # Return empty list if there's an error (e.g., table doesn't exist yet)
        return []


def save_medication_reminder(
    db: Session,
    session_id: str,
    medication_name: str,
    dosage: str,
    frequency: str,
    duration_days: int,
    notes: Optional[str] = None
) -> MedicationReminder:
    """Save medication reminder to database"""
    from datetime import timedelta
    start_date = datetime.now()
    end_date = start_date + timedelta(days=duration_days)
    
    reminder = MedicationReminder(
        session_id=session_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        duration_days=duration_days,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
        is_active=1
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def get_medication_reminders(db: Session, session_id: str, active_only: bool = True) -> List[MedicationReminder]:
    """Get medication reminders for a session"""
    query = db.query(MedicationReminder).filter(
        MedicationReminder.session_id == session_id
    )
    if active_only:
        query = query.filter(MedicationReminder.is_active == 1)
    return query.order_by(MedicationReminder.created_at.desc()).all()


def deactivate_medication_reminder(db: Session, reminder_id: int) -> bool:
    """Deactivate a medication reminder"""
    reminder = db.query(MedicationReminder).filter(MedicationReminder.id == reminder_id).first()
    if reminder:
        reminder.is_active = 0
        db.commit()
        return True
    return False

