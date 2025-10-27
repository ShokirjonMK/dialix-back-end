"""
AI Chat Router

AI Chat interface uchun API endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from uuid import UUID

from backend.schemas import AIChatMessageRequest, ChatSessionResponse
from backend.services import ai_chat
from backend import db
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.utils.shortcuts import model_to_dict
from backend.schemas import AIChatMessage as AIChatMessageSchema

ai_chat_router = APIRouter(tags=["AI Chat"])
MAX_QUESTIONS_PER_SESSION = 10


@ai_chat_router.post("/chat/session")
def create_chat_session(
    record_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Yangi AI chat session yaratish"""
    try:
        session = ai_chat.create_chat_session(db_session, current_user.id, record_id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "session_id": str(session.id),
                "remaining_questions": MAX_QUESTIONS_PER_SESSION,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@ai_chat_router.post("/chat/{session_id}/message")
def send_message(
    session_id: UUID,
    message_data: AIChatMessageRequest,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """AI'ga xabar yuborish"""
    try:
        # Get session
        session = ai_chat.get_session_by_id(db_session, session_id)
        if not session:
            raise HTTPException(404, "Session not found")

        if session.user_id != current_user.id:
            raise HTTPException(403, "Access denied")

        # Check question limit
        if not ai_chat.check_question_limit(session):
            raise HTTPException(
                400,
                f"Question limit reached ({MAX_QUESTIONS_PER_SESSION} questions per session)",
            )

        # Get record for context
        record_dict = db.get_record_by_id(str(session.record_id), str(current_user.id))
        if not record_dict:
            raise HTTPException(404, "Record not found")

        # Extract context from dict
        context = {
            "record_id": str(session.record_id),
            "title": record_dict.get("title", ""),
            "duration": record_dict.get("duration", 0),
            "operator_code": record_dict.get("operator_code", ""),
            "operator_name": record_dict.get("operator_name", ""),
            "call_type": record_dict.get("call_type", ""),
            "client_phone_number": record_dict.get("client_phone_number", ""),
        }

        # Extract conversation text from payload if available
        if record_dict.get("payload"):
            payload_data = (
                record_dict.get("payload")
                if isinstance(record_dict.get("payload"), dict)
                else {}
            )
            context["conversation_text"] = payload_data.get("result", {}).get(
                "conversation_text", ""
            )
            context["transcription"] = payload_data.get("result", {}).get(
                "transcription", ""
            )

        # TODO: Implement actual AI response
        # For now, return a placeholder
        response_text = f"This is a placeholder response for: {message_data.message}"

        # Save messages
        ai_chat.add_message_to_session(
            db_session, session_id, "user", message_data.message
        )
        ai_chat.add_message_to_session(
            db_session, session_id, "assistant", response_text
        )

        # Increment question count
        ai_chat.increment_question_count(db_session, session_id)

        # Get updated session
        updated_session = ai_chat.get_session_by_id(db_session, session_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "response": response_text,
                "remaining_questions": MAX_QUESTIONS_PER_SESSION
                - updated_session.session_data.get("questions_asked", 0),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ai_chat_router.get("/chat/suggested-questions/{record_id}")
def get_suggested_questions(
    record_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Context'ga asoslangan savollarni olish"""
    try:
        # Get record as dict
        record_dict = db.get_record_by_id(str(record_id), str(current_user.id))

        if not record_dict:
            raise HTTPException(404, "Record not found")

        # Basic suggested questions
        questions = [
            "Qo'ng'iroqda qanday asosiy mavzular muhokama qilindi?",
            "Mijozning asosiy ehtiyoji nima edi?",
            "Operator qanday savollar berdi?",
            "Suhbatning umumiy sentiment holati qanday?",
            "Qaysi kurslar haqida gapirildi?",
        ]

        # If payload exists, add more specific questions
        if record_dict.get("payload"):
            payload_data = (
                record_dict.get("payload")
                if isinstance(record_dict.get("payload"), dict)
                else {}
            )

            # Add sentiment-specific questions
            if payload_data.get("sentiment_analysis_of_conversation"):
                questions.append(
                    f"Qanday sabab conversation sentimenti '{payload_data.get('sentiment_analysis_of_conversation')}' bo'ldi?"
                )

            # Add customer interest questions
            if payload_data.get("which_course_customer_interested"):
                questions.append("Mijoz qaysi kurslar bilan qiziqdi?")

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"questions": questions}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ai_chat_router.get("/chat/session/{session_id}/messages")
def get_chat_history(
    session_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Chat tarixini olish"""
    session = ai_chat.get_session_by_id(db_session, session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    if session.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    messages = ai_chat.get_session_messages(db_session, session_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"messages": [model_to_dict(AIChatMessageSchema, m) for m in messages]},
    )
