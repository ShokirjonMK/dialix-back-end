"""
AI Chat Service

AI Chat interface uchun service layer
"""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func

from backend.database.models import AIChatSession, AIChatMessage, Record
from backend.utils.auth import hashify


MAX_QUESTIONS_PER_SESSION = 10


def create_chat_session(db: Session, user_id: UUID, record_id: UUID) -> AIChatSession:
    """Yangi AI chat session yaratish"""
    # Check if record exists
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise ValueError("Record not found")

    # Check if record belongs to user
    if str(record.owner_id) != str(user_id):
        raise PermissionError("Access denied to this record")

    session = AIChatSession(
        user_id=user_id,
        record_id=record_id,
        session_data={"questions_asked": 0, "context": {}},
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logging.info(f"Chat session created: {session.id} for record {record_id}")
    return session


def get_session_by_id(db: Session, session_id: UUID) -> Optional[AIChatSession]:
    """Session ma'lumotini olish"""
    return db.query(AIChatSession).filter(AIChatSession.id == session_id).first()


def check_question_limit(session: AIChatSession) -> bool:
    """Savollar limitiga tekshirish"""
    return session.session_data.get("questions_asked", 0) < MAX_QUESTIONS_PER_SESSION


def add_message_to_session(
    db: Session, session_id: UUID, role: str, content: str
) -> AIChatMessage:
    """Xabar qo'shish"""
    message = AIChatMessage(session_id=session_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def increment_question_count(db: Session, session_id: UUID):
    """Savollar sonini oshirish"""
    session = get_session_by_id(db, session_id)
    if session:
        current_count = session.session_data.get("questions_asked", 0)
        session.session_data["questions_asked"] = current_count + 1
        db.commit()


def get_session_messages(db: Session, session_id: UUID) -> list[AIChatMessage]:
    """Session xabarlarini olish"""
    return (
        db.query(AIChatMessage)
        .filter(AIChatMessage.session_id == session_id)
        .order_by(AIChatMessage.created_at)
        .all()
    )


def get_suggested_questions(record: Record) -> list[str]:
    """Context'ga asoslangan taklif etilgan savollar"""
    # Basic suggested questions
    questions = [
        "Qo'ng'iroqda qanday asosiy mavzular muhokama qilindi?",
        "Mijozning asosiy ehtiyoji nima edi?",
        "Operator qanday savollar berdi?",
        "Suhbatning umumiy sentiment holati qanday?",
        "Qaysi kurslar haqida gapirildi?",
    ]

    # If payload exists, add more specific questions
    if record.payload:
        payload_data = record.payload if isinstance(record.payload, dict) else {}

        # Add sentiment-specific questions
        if payload_data.get("sentiment_analysis_of_conversation"):
            questions.append(
                f"Qanday sabab conversation sentimenti '{payload_data.get('sentiment_analysis_of_conversation')}' bo'ldi?"
            )

        # Add customer interest questions
        if payload_data.get("which_course_customer_interested"):
            questions.append("Mijoz qaysi kurslar bilan qiziqdi?")

    return questions


def extract_context_from_record(record: Record) -> dict:
    """Record dan context extract qilish"""
    context = {
        "record_id": str(record.id),
        "title": record.title,
        "duration": record.duration,
        "operator_code": record.operator_code,
        "operator_name": record.operator_name,
        "call_type": record.call_type,
        "client_phone_number": record.client_phone_number,
    }

    # Extract conversation text from payload if available
    if record.payload:
        payload_data = record.payload if isinstance(record.payload, dict) else {}
        context["conversation_text"] = payload_data.get("result", {}).get(
            "conversation_text", ""
        )
        context["transcription"] = payload_data.get("result", {}).get(
            "transcription", ""
        )

    return context
