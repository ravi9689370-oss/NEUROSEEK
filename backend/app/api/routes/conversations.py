"""Conversations API routes."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetail,
    MessageCreate,
    MessageResponse,
    FeedbackRequest,
)

router = APIRouter()


async def get_current_user_id(request) -> Optional[uuid.UUID]:
    """Extract user ID from auth header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    user_id_str = decode_access_token(token)
    return uuid.UUID(user_id_str) if user_id_str else None


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request,
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    user_id = await get_current_user_id(request)
    
    conv = Conversation(
        user_id=user_id,
        title=conversation.title,
        system_prompt=conversation.system_prompt,
        model_used=conversation.model_used,
        metadata=conversation.metadata,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        system_prompt=conv.system_prompt,
        model_used=conv.model_used,
        routing_intent=conv.routing_intent,
        is_archived=conv.is_archived,
        is_pinned=conv.is_pinned,
        metadata=conv.metadata,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    archived: Optional[bool] = None,
    pinned: Optional[bool] = None,
):
    """List conversations for current user."""
    user_id = await get_current_user_id(request)
    
    query = select(Conversation).where(Conversation.user_id == user_id)
    
    if archived is not None:
        query = query.where(Conversation.is_archived == archived)
    if pinned is not None:
        query = query.where(Conversation.is_pinned == pinned)
    
    query = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Get message counts
    conv_ids = [c.id for c in conversations]
    if conv_ids:
        msg_counts = await db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(Message.conversation_id.in_(conv_ids))
            .group_by(Message.conversation_id)
        )
        count_map = dict(msg_counts.all())
    else:
        count_map = {}
    
    return [
        ConversationResponse(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            system_prompt=c.system_prompt,
            model_used=c.model_used,
            routing_intent=c.routing_intent,
            is_archived=c.is_archived,
            is_pinned=c.is_pinned,
            metadata=c.metadata,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=count_map.get(c.id, 0),
        )
        for c in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    return ConversationDetail(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        system_prompt=conversation.system_prompt,
        model_used=conversation.model_used,
        routing_intent=conversation.routing_intent,
        is_archived=conversation.is_archived,
        is_pinned=conversation.is_pinned,
        metadata=conversation.metadata,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role.value,
                content=m.content,
                model=m.model,
                provider=m.provider,
                prompt_tokens=m.prompt_tokens,
                completion_tokens=m.completion_tokens,
                total_tokens=m.total_tokens,
                generation_time_ms=m.generation_time_ms,
                time_to_first_token_ms=m.time_to_first_token_ms,
                feedback=m.feedback.value if m.feedback else None,
                is_training_candidate=m.is_training_candidate,
                created_at=m.created_at,
                metadata=m.metadata,
            )
            for m in sorted(conversation.messages, key=lambda m: m.created_at)
        ],
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    update: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update conversation metadata."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    if update.title is not None:
        conversation.title = update.title
    if update.system_prompt is not None:
        conversation.system_prompt = update.system_prompt
    if update.is_archived is not None:
        conversation.is_archived = update.is_archived
    if update.is_pinned is not None:
        conversation.is_pinned = update.is_pinned
    if update.metadata is not None:
        conversation.metadata = update.metadata
    
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        system_prompt=conversation.system_prompt,
        model_used=conversation.model_used,
        routing_intent=conversation.routing_intent,
        is_archived=conversation.is_archived,
        is_pinned=conversation.is_pinned,
        metadata=conversation.metadata,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"success": True, "message": "Conversation deleted"}


@router.post("/{conversation_id}/branch", response_model=ConversationResponse)
async def branch_conversation(
    conversation_id: uuid.UUID,
    branch_from_message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation branched from a specific message."""
    # Get original conversation
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(404, "Conversation not found")
    
    # Find branch point
    branch_msg = next((m for m in original.messages if m.id == branch_from_message_id), None)
    if not branch_msg:
        raise HTTPException(404, "Branch message not found")
    
    # Create new conversation with messages up to branch point
    new_conv = Conversation(
        user_id=original.user_id,
        title=f"Branch of: {original.title or 'Untitled'}",
        system_prompt=original.system_prompt,
        model_used=original.model_used,
        metadata={**original.metadata, "branched_from": str(conversation_id)},
        parent_id=conversation_id,
        branch_from_message_id=branch_from_message_id,
    )
    db.add(new_conv)
    await db.flush()
    
    # Copy messages up to branch point
    messages_up_to_branch = [
        m for m in sorted(original.messages, key=lambda m: m.created_at)
        if m.created_at <= branch_msg.created_at
    ]
    
    for msg in messages_up_to_branch:
        new_msg = Message(
            conversation_id=new_conv.id,
            role=msg.role,
            content=msg.content,
            model=msg.model,
            provider=msg.provider,
            prompt_tokens=msg.prompt_tokens,
            completion_tokens=msg.completion_tokens,
            total_tokens=msg.total_tokens,
            temperature=msg.temperature,
            top_p=msg.top_p,
            max_tokens=msg.max_tokens,
            generation_time_ms=msg.generation_time_ms,
            time_to_first_token_ms=msg.time_to_first_token_ms,
            metadata={**msg.metadata, "branched": True},
        )
        db.add(new_msg)
    
    await db.commit()
    await db.refresh(new_conv)
    
    return ConversationResponse(
        id=new_conv.id,
        user_id=new_conv.user_id,
        title=new_conv.title,
        system_prompt=new_conv.system_prompt,
        model_used=new_conv.model_used,
        routing_intent=new_conv.routing_intent,
        is_archived=new_conv.is_archived,
        is_pinned=new_conv.is_pinned,
        metadata=new_conv.metadata,
        created_at=new_conv.created_at,
        updated_at=new_conv.updated_at,
        message_count=len(messages_up_to_branch),
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: uuid.UUID,
    message: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a message to conversation (for manual history building)."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    msg = Message(
        conversation_id=conversation_id,
        role=MessageRole(message.role),
        content=message.content,
        model=message.model,
        provider=message.provider,
        temperature=message.temperature,
        top_p=message.top_p,
        max_tokens=message.max_tokens,
    )
    db.add(msg)
    
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role.value,
        content=msg.content,
        model=msg.model,
        provider=msg.provider,
        prompt_tokens=msg.prompt_tokens,
        completion_tokens=msg.completion_tokens,
        total_tokens=msg.total_tokens,
        generation_time_ms=msg.generation_time_ms,
        time_to_first_token_ms=msg.time_to_first_token_ms,
        feedback=msg.feedback.value if msg.feedback else None,
        is_training_candidate=msg.is_training_candidate,
        created_at=msg.created_at,
        metadata=msg.metadata,
    )


@router.post("/{conversation_id}/feedback")
async def submit_feedback(
    conversation_id: uuid.UUID,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on a message."""
    result = await db.execute(select(Message).where(Message.id == feedback.message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(404, "Message not found")
    
    if message.conversation_id != conversation_id:
        raise HTTPException(400, "Message not in this conversation")
    
    from app.models.conversation import MessageFeedback
    message.feedback = MessageFeedback(feedback.feedback)
    message.feedback_note = feedback.feedback_note
    
    if feedback.feedback == "edited" and feedback.edited_content:
        message.metadata["original_content"] = message.content
        message.content = feedback.edited_content
    
    # Mark as training candidate for positive feedback
    if feedback.feedback in ["positive", "edited"]:
        message.is_training_candidate = True
        message.training_weight = 1.0
    elif feedback.feedback == "negative":
        message.is_training_candidate = True
        message.training_weight = 0.5
    
    await db.commit()
    
    return {"success": True, "message": "Feedback recorded"}