"""Feedback API routes."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Message, MessageFeedback
from app.schemas import FeedbackRequest

router = APIRouter()


@router.post("")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on a message."""
    result = await db.execute(select(Message).where(Message.id == feedback.message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(404, "Message not found")
    
    message.feedback = MessageFeedback(feedback.feedback)
    message.feedback_note = feedback.feedback_note
    
    if feedback.feedback == "edited" and feedback.edited_content:
        message.metadata["original_content"] = message.content
        message.content = feedback.edited_content
    
    # Mark as training candidate
    if feedback.feedback in ["positive", "edited"]:
        message.is_training_candidate = True
        message.training_weight = 1.0
    elif feedback.feedback == "negative":
        message.is_training_candidate = True
        message.training_weight = 0.5
    
    await db.commit()
    
    return {"success": True, "message": "Feedback recorded"}


@router.get("/stats")
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    model: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
):
    """Get feedback statistics."""
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = select(
        Message.feedback,
        func.count(Message.id)
    ).where(
        and_(
            Message.created_at >= cutoff,
            Message.feedback.isnot(None),
        )
    )
    
    if model:
        query = query.where(Message.model == model)
    
    query = query.group_by(Message.feedback)
    result = await db.execute(query)
    stats = dict(result.all())
    
    # Total messages in period
    total_query = select(func.count(Message.id)).where(Message.created_at >= cutoff)
    if model:
        total_query = total_query.where(Message.model == model)
    total = await db.execute(total_query)
    
    return {
        "period_days": days,
        "total_messages": total.scalar(),
        "feedback_breakdown": {k.value if hasattr(k, 'value') else k: v for k, v in stats.items()},
        "feedback_rate": sum(stats.values()) / total.scalar() if total.scalar() > 0 else 0,
    }


@router.get("/training-candidates")
async def training_candidates(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    min_weight: float = Query(0.5, ge=0, le=1),
):
    """Get messages marked as training candidates."""
    result = await db.execute(
        select(Message)
        .where(
            and_(
                Message.is_training_candidate == True,
                Message.training_weight >= min_weight,
            )
        )
        .order_by(desc(Message.training_weight), desc(Message.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return [
        {
            "id": str(m.id),
            "conversation_id": str(m.conversation_id),
            "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
            "feedback": m.feedback.value if m.feedback else None,
            "training_weight": m.training_weight,
            "model": m.model,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/batch")
async def batch_feedback(
    feedbacks: List[FeedbackRequest],
    db: AsyncSession = Depends(get_db),
):
    """Submit multiple feedback at once."""
    results = []
    
    for feedback in feedbacks:
        result = await db.execute(select(Message).where(Message.id == feedback.message_id))
        message = result.scalar_one_or_none()
        
        if not message:
            results.append({"message_id": str(feedback.message_id), "success": False, "error": "Not found"})
            continue
        
        message.feedback = MessageFeedback(feedback.feedback)
        message.feedback_note = feedback.feedback_note
        
        if feedback.feedback == "edited" and feedback.edited_content:
            message.metadata["original_content"] = message.content
            message.content = feedback.edited_content
        
        if feedback.feedback in ["positive", "edited"]:
            message.is_training_candidate = True
            message.training_weight = 1.0
        elif feedback.feedback == "negative":
            message.is_training_candidate = True
            message.training_weight = 0.5
        
        results.append({"message_id": str(feedback.message_id), "success": True})
    
    await db.commit()
    
    return {"results": results}