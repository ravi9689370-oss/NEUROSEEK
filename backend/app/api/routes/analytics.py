"""Analytics API routes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Conversation, Message, MessageFeedback
from app.models.model_registry import ModelRegistry
from app.models.training import TrainingRun, TrainingStatus

router = APIRouter()


@router.get("/model-performance", response_model=List[dict])
async def model_performance(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    min_requests: int = Query(10, ge=1),
):
    """Get performance metrics per model."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get messages with model info
    result = await db.execute(
        select(
            Message.model,
            func.count(Message.id).label("total_requests"),
            func.avg(Message.generation_time_ms).label("avg_latency_ms"),
            func.avg(Message.completion_tokens * 1000.0 / Message.generation_time_ms).label("avg_tps"),
            func.sum(case_when(Message.feedback == MessageFeedback.POSITIVE, 1, 0)).label("positive"),
            func.sum(case_when(Message.feedback == MessageFeedback.NEGATIVE, 1, 0)).label("negative"),
            func.sum(case_when(Message.is_training_candidate == True, 1, 0)).label("training_candidates"),
        )
        .where(and_(Message.created_at >= cutoff, Message.model.isnot(None)))
        .group_by(Message.model)
        .having(func.count(Message.id) >= min_requests)
    )
    
    metrics = []
    for row in result.all():
        total_feedback = (row.positive or 0) + (row.negative or 0)
        feedback_score = (row.positive or 0) / total_feedback if total_feedback > 0 else 0
        
        metrics.append({
            "model": row.model,
            "total_requests": row.total_requests,
            "avg_latency_ms": round(row.avg_latency_ms or 0, 2),
            "avg_tokens_per_sec": round(row.avg_tps or 0, 2),
            "positive_feedback": row.positive or 0,
            "negative_feedback": row.negative or 0,
            "feedback_score": round(feedback_score, 3),
            "training_candidates": row.training_candidates or 0,
        })
    
    return sorted(metrics, key=lambda x: x["total_requests"], reverse=True)


@router.get("/routing-stats", response_model=List[dict])
async def routing_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get routing statistics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(
            Conversation.routing_intent,
            func.count(Conversation.id).label("count"),
            func.avg(Message.generation_time_ms).label("avg_latency_ms"),
        )
        .select_from(Conversation)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(and_(Conversation.created_at >= cutoff, Conversation.routing_intent.isnot(None)))
        .group_by(Conversation.routing_intent)
    )
    
    stats = []
    for row in result.all():
        # Get models used for this intent
        models_result = await db.execute(
            select(Message.model, func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(and_(
                Conversation.routing_intent == row.routing_intent,
                Conversation.created_at >= cutoff,
                Message.model.isnot(None),
            ))
            .group_by(Message.model)
        )
        models_used = dict(models_result.all())
        
        stats.append({
            "intent": row.routing_intent,
            "count": row.count,
            "avg_latency_ms": round(row.avg_latency_ms or 0, 2),
            "models_used": models_used,
        })
    
    return sorted(stats, key=lambda x: x["count"], reverse=True)


@router.get("/training-progress", response_model=List[dict])
async def training_progress(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent training progress."""
    result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.status.in_([
            TrainingStatus.RUNNING,
            TrainingStatus.EVALUATING,
            TrainingStatus.COMPLETED,
            TrainingStatus.FAILED,
        ]))
        .order_by(desc(TrainingRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    
    return [
        {
            "run_id": str(r.id),
            "name": r.name,
            "method": r.method.value,
            "status": r.status.value,
            "progress": round(r.progress * 100, 1),
            "current_step": r.current_step,
            "total_steps": r.total_steps,
            "current_epoch": round(r.current_epoch, 2),
            "train_loss": r.train_loss,
            "val_loss": r.val_loss,
            "improvement_score": r.improvement_score,
            "passed_evaluation": r.passed_evaluation,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/usage-overview")
async def usage_overview(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get overall usage statistics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Conversations
    conv_count = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.created_at >= cutoff)
    )
    
    # Messages
    msg_count = await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= cutoff)
    )
    
    # Unique users
    user_count = await db.execute(
        select(func.count(func.distinct(Conversation.user_id)))
        .where(and_(Conversation.created_at >= cutoff, Conversation.user_id.isnot(None)))
    )
    
    # Total tokens
    tokens = await db.execute(
        select(func.sum(Message.total_tokens)).where(Message.created_at >= cutoff)
    )
    
    # Avg conversation length
    avg_len = await db.execute(
        select(func.avg(func.count(Message.id)))
        .select_from(Conversation)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.created_at >= cutoff)
        .group_by(Conversation.id)
    )
    
    # Feedback stats
    feedback_stats = await db.execute(
        select(
            Message.feedback,
            func.count(Message.id)
        )
        .where(and_(Message.created_at >= cutoff, Message.feedback.isnot(None)))
        .group_by(Message.feedback)
    )
    
    return {
        "period_days": days,
        "total_conversations": conv_count.scalar() or 0,
        "total_messages": msg_count.scalar() or 0,
        "active_users": user_count.scalar() or 0,
        "total_tokens": tokens.scalar() or 0,
        "avg_conversation_length": round(avg_len.scalar() or 0, 1),
        "feedback_breakdown": {k.value if hasattr(k, 'value') else k: v for k, v in feedback_stats.all()},
    }


@router.get("/conversation-trends")
async def conversation_trends(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", pattern="^(hour|day|week)$"),
):
    """Get conversation trends over time."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Determine date truncation
    if granularity == "hour":
        date_trunc = func.date_trunc('hour', Conversation.created_at)
    elif granularity == "week":
        date_trunc = func.date_trunc('week', Conversation.created_at)
    else:
        date_trunc = func.date_trunc('day', Conversation.created_at)
    
    result = await db.execute(
        select(
            date_trunc.label("period"),
            func.count(Conversation.id).label("conversations"),
            func.count(func.distinct(Conversation.user_id)).label("users"),
        )
        .where(Conversation.created_at >= cutoff)
        .group_by(date_trunc)
        .order_by(date_trunc)
    )
    
    return [
        {
            "period": row.period.isoformat(),
            "conversations": row.conversations,
            "users": row.users,
        }
        for row in result.all()
    ]


# Helper for conditional aggregation
from sqlalchemy import case

def case_when(condition, true_val, false_val):
    return func.sum(case((condition, true_val), else_=false_val))