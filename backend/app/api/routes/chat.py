"""Chat and inference API routes."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.conversation import Conversation, Message, MessageRole, MessageFeedback
from app.models.model_registry import ModelRegistry
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
    ConversationCreate,
    ConversationResponse,
    ConversationDetail,
    MessageResponse,
    StreamingChatResponse,
)
from app.services.inference.engine import InferenceEngine, get_inference_engine
from app.services.routing.router import ModelRouter, get_model_router
from app.services.routing.ensemble import EnsembleManager, get_ensemble_manager

router = APIRouter()
settings = get_settings()


async def get_current_user_id(request: Request) -> Optional[str]:
    """Extract user ID from auth header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    return decode_access_token(token)


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    request_obj: Request,
    db: AsyncSession = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
    model_router: ModelRouter = Depends(get_model_router),
    ensemble_manager: EnsembleManager = Depends(get_ensemble_manager),
):
    """Main chat completions endpoint - supports streaming and ensemble."""
    user_id = await get_current_user_id(request_obj)
    
    # Validate messages
    if not request.messages:
        raise HTTPException(400, "Messages cannot be empty")
    
    # Get or create conversation
    conversation = None
    if request.metadata.get("conversation_id"):
        conv_id = request.metadata["conversation_id"]
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conv_id)
            .options(selectinload(Conversation.messages))
        )
        conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            user_id=uuid.UUID(user_id) if user_id else None,
            title=request.metadata.get("title"),
            system_prompt=request.metadata.get("system_prompt"),
            metadata=request.metadata,
        )
        db.add(conversation)
        await db.flush()
    
    # Convert messages to dict format
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Determine model
    model = request.model
    routing_info = None
    
    if not model or request.use_ensemble:
        # Use smart routing
        routing_decision = await model_router.route(
            query=request.messages[-1].content,
            context=[{"role": m.role, "content": m.content} for m in request.messages[:-1]],
            preferred_model=model,
        )
        model = routing_decision.model
        routing_info = {
            "intent": routing_decision.intent,
            "confidence": routing_decision.confidence,
            "reasoning": routing_decision.reasoning,
            "alternatives": routing_decision.alternatives,
        }
    
    # Validate model exists
    model_exists = await engine.is_model_available(model)
    if not model_exists:
        # Try to pull
        try:
            async for _ in engine.pull_model(model):
                pass
        except Exception:
            raise HTTPException(404, f"Model {model} not available")
    
    if request.stream:
        return StreamingResponse(
            stream_chat_response(
                request=request,
                conversation=conversation,
                model=model,
                engine=engine,
                ensemble_manager=ensemble_manager,
                routing_info=routing_info,
                db=db,
            ),
            media_type="text/event-stream",
        )
    
    # Non-streaming
    if request.use_ensemble and request.ensemble_models:
        ensemble_result = await ensemble_manager.run_ensemble(
            messages=messages,
            models=request.ensemble_models,
            system=request.metadata.get("system_prompt"),
            temperature=request.temperature,
        )
        response_text = ensemble_result.synthesized_answer
        model = ensemble_result.synthesis_model
        prompt_tokens = sum(r.prompt_tokens for r in ensemble_result.model_responses.values())
        completion_tokens = sum(r.completion_tokens for r in ensemble_result.model_responses.values())
        generation_time_ms = ensemble_result.total_time_ms
    else:
        result = await engine.generate(
            model=model,
            messages=messages,
            system=request.metadata.get("system_prompt"),
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            max_tokens=request.max_tokens,
            stream=False,
        )
        response_text = result.text
        prompt_tokens = result.prompt_tokens
        completion_tokens = result.completion_tokens
        generation_time_ms = result.generation_time_ms
    
    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=response_text,
        model=model,
        provider="ollama",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        max_tokens=request.max_tokens,
        generation_time_ms=generation_time_ms,
        metadata={"routing_info": routing_info} if routing_info else {},
    )
    db.add(assistant_msg)
    
    # Update conversation
    conversation.model_used = model
    conversation.updated_at = datetime.now(timezone.utc)
    if routing_info:
        conversation.routing_intent = routing_info.get("intent")
    
    await db.commit()
    
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(datetime.now(timezone.utc).timestamp()),
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        routing_info=routing_info,
    )


async def stream_chat_response(
    request: ChatCompletionRequest,
    conversation: Conversation,
    model: str,
    engine: InferenceEngine,
    ensemble_manager: EnsembleManager,
    routing_info: Optional[dict],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream chat response as SSE."""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(datetime.now(timezone.utc).timestamp())
    
    accumulated_text = ""
    prompt_tokens = 0
    completion_tokens = 0
    
    try:
        if request.use_ensemble and request.ensemble_models:
            # Stream ensemble
            async for chunk in ensemble_manager.run_ensemble_stream(
                messages=messages,
                models=request.ensemble_models,
                system=request.metadata.get("system_prompt"),
                temperature=request.temperature,
            ):
                if chunk["type"] == "token":
                    accumulated_text += chunk["text"]
                    yield format_sse_chunk(
                        response_id, created, model, chunk["text"], False
                    )
                elif chunk["type"] == "synthesis":
                    # Final synthesized response
                    accumulated_text = chunk["text"]
                    model = chunk["model"]
                    yield format_sse_chunk(
                        response_id, created, model, chunk["text"], True
                    )
        else:
            # Stream single model
            async for chunk in engine.generate(
                model=model,
                messages=messages,
                system=request.metadata.get("system_prompt"),
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                max_tokens=request.max_tokens,
                stream=True,
            ):
                if chunk.text:
                    accumulated_text += chunk.text
                    yield format_sse_chunk(
                        response_id, created, model, chunk.text, chunk.is_final
                    )
                
                if chunk.is_final and chunk.usage:
                    prompt_tokens = chunk.usage.get("prompt_tokens", 0)
                    completion_tokens = chunk.usage.get("completion_tokens", 0)
        
        # Save final message
        async with get_db() as save_db:
            assistant_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=accumulated_text,
                model=model,
                provider="ollama",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
                metadata={"routing_info": routing_info} if routing_info else {},
            )
            save_db.add(assistant_msg)
            
            conv = await save_db.get(Conversation, conversation.id)
            if conv:
                conv.model_used = model
                conv.updated_at = datetime.now(timezone.utc)
                if routing_info:
                    conv.routing_intent = routing_info.get("intent")
            
            await save_db.commit()
        
        # Final chunk with usage
        yield format_sse_chunk(
            response_id, created, model, "", True,
            usage={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
        )
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield format_sse_error(response_id, created, model, str(e))


def format_sse_chunk(
    response_id: str,
    created: int,
    model: str,
    content: str,
    is_final: bool,
    usage: Optional[dict] = None,
) -> str:
    """Format SSE chunk."""
    choice = {
        "index": 0,
        "delta": {"content": content} if content else {},
        "finish_reason": "stop" if is_final else None,
    }
    if usage:
        choice["delta"]["usage"] = usage
    
    chunk = StreamingChatResponse(
        id=response_id,
        created=created,
        model=model,
        choices=[choice],
    )
    return f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"


def format_sse_error(response_id: str, created: int, model: str, error: str) -> str:
    """Format SSE error chunk."""
    chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "error",
        }],
        "error": {"message": error, "type": "server_error"},
    }
    import json
    return f"data: {json.dumps(chunk)}\n\n"


@router.post("/ensemble", response_model=ChatCompletionResponse)
async def chat_ensemble(
    request: ChatCompletionRequest,
    request_obj: Request,
    db: AsyncSession = Depends(get_db),
    ensemble_manager: EnsembleManager = Depends(get_ensemble_manager),
):
    """Run ensemble inference with multiple models."""
    user_id = await get_current_user_id(request_obj)
    
    if not request.ensemble_models:
        raise HTTPException(400, "ensemble_models required for ensemble endpoint")
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    ensemble_result = await ensemble_manager.run_ensemble(
        messages=messages,
        models=request.ensemble_models,
        system=request.metadata.get("system_prompt"),
        temperature=request.temperature,
    )
    
    # Save conversation
    conversation = Conversation(
        user_id=uuid.UUID(user_id) if user_id else None,
        title=request.metadata.get("title"),
        model_used=ensemble_result.synthesis_model,
        metadata=request.metadata,
    )
    db.add(conversation)
    await db.flush()
    
    # Save messages
    for msg in request.messages:
        db.add(Message(
            conversation_id=conversation.id,
            role=MessageRole(msg.role),
            content=msg.content,
        ))
    
    # Save assistant response
    db.add(Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=ensemble_result.synthesized_answer,
        model=ensemble_result.synthesis_model,
        provider="ensemble",
        prompt_tokens=sum(r.prompt_tokens for r in ensemble_result.model_responses.values()),
        completion_tokens=sum(r.completion_tokens for r in ensemble_result.model_responses.values()),
        total_tokens=sum(r.total_tokens for r in ensemble_result.model_responses.values()),
        generation_time_ms=ensemble_result.total_time_ms,
        metadata={
            "ensemble": True,
            "model_responses": {
                m: {
                    "text": r.text[:200],
                    "tokens": r.total_tokens,
                    "time_ms": r.generation_time_ms,
                }
                for m, r in ensemble_result.model_responses.items()
            },
        },
    ))
    
    await db.commit()
    
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(datetime.now(timezone.utc).timestamp()),
        model=ensemble_result.synthesis_model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=ensemble_result.synthesized_answer),
                finish_reason="stop",
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=sum(r.prompt_tokens for r in ensemble_result.model_responses.values()),
            completion_tokens=sum(r.completion_tokens for r in ensemble_result.model_responses.values()),
            total_tokens=sum(r.total_tokens for r in ensemble_result.model_responses.values()),
        ),
        routing_info={
            "ensemble": True,
            "models_used": list(ensemble_result.model_responses.keys()),
            "synthesis_model": ensemble_result.synthesis_model,
        },
    )


@router.get("/models")
async def list_models(engine: InferenceEngine = Depends(get_inference_engine)):
    """List available models."""
    models = await engine.list_models()
    return {"models": models}


@router.post("/models/pull")
async def pull_model(name: str, engine: InferenceEngine = Depends(get_inference_engine)):
    """Pull/download a model."""
    async def progress_stream():
        async for progress in engine.pull_model(name):
            import json
            yield f"data: {json.dumps(progress)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(progress_stream(), media_type="text/event-stream")


@router.get("/models/{model_name}/info")
async def model_info(model_name: str, engine: InferenceEngine = Depends(get_inference_engine)):
    """Get model information."""
    if hasattr(engine, '_ollama') and engine._ollama:
        info = await engine._ollama.show_model_info(model_name)
        return info
    return {"name": model_name, "error": "Model info not available"}