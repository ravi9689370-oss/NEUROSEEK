"""Main inference engine combining Ollama and llama.cpp."""
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional, Any

import structlog

from app.core.config import get_settings
from app.services.inference.ollama_client import OllamaClient, get_ollama_client
from app.services.inference.llama_cpp_client import LlamaCppClient, get_llama_cpp_client

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class GenerationResult:
    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    generation_time_ms: int
    time_to_first_token_ms: Optional[int] = None
    finish_reason: str = "stop"


@dataclass
class StreamingChunk:
    text: str
    is_final: bool
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class InferenceEngine:
    """Unified inference engine supporting multiple backends."""
    
    def __init__(self):
        self._ollama: Optional[OllamaClient] = None
        self._llama_cpp_clients: Dict[str, LlamaCppClient] = {}
        self._model_cache: Dict[str, Dict] = {}
        _cache_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize engine and load model info."""
        self._ollama = await get_ollama_client()
        await self._refresh_model_cache()
        logger.info("inference_engine_initialized", models=len(self._model_cache))
    
    async def _refresh_model_cache(self) -> None:
        """Refresh available models from Ollama."""
        if not self._ollama:
            return
        try:
            models = await self._ollama.list_models()
            self._model_cache = {m["name"]: m for m in models}
        except Exception as e:
            logger.warning("model_cache_refresh_failed", error=str(e))
    
    async def list_models(self) -> List[Dict[str, Any]]:
        await self._refresh_model_cache()
        return list(self._model_cache.values())
    
    async def is_model_available(self, model: str) -> bool:
        await self._refresh_model_cache()
        return model in self._model_cache
    
    async def pull_model(self, model: str) -> AsyncGenerator[Dict, None]:
        if not self._ollama:
            raise RuntimeError("Ollama not initialized")
        async for progress in self._ollama.pull_model(model):
            yield progress
        await self._refresh_model_cache()
    
    async def delete_model(self, model: str) -> bool:
        if not self._ollama:
            raise RuntimeError("Ollama not initialized")
        result = await self._ollama.delete_model(model)
        await self._refresh_model_cache()
        return result
    
    def _get_default_options(self, overrides: Optional[Dict] = None) -> Dict[str, Any]:
        gen = settings.inference.generation
        options = {
            "temperature": gen.temperature,
            "top_p": gen.top_p,
            "top_k": gen.top_k,
            "num_predict": gen.max_tokens,
            "repeat_penalty": gen.repeat_penalty,
        }
        if gen.stop_sequences:
            options["stop"] = gen.stop_sequences
        if overrides:
            options.update(overrides)
        return options
    
    def _format_messages_for_ollama(
        self, messages: List[Dict[str, str]], system: Optional[str] = None
    ) -> List[Dict[str, str]]:
        formatted = []
        if system:
            formatted.append({"role": "system", "content": system})
        formatted.extend(messages)
        return formatted
    
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> GenerationResult | AsyncGenerator[StreamingChunk, None]:
        """Generate completion using Ollama."""
        if not self._ollama:
            raise RuntimeError("Inference engine not initialized")
        
        options = self._get_default_options()
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if stop:
            options["stop"] = stop
        
        formatted_messages = self._format_messages_for_ollama(messages, system)
        
        start_time = time.time()
        first_token_time = None
        accumulated_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        if stream:
            return self._stream_generate(
                model, formatted_messages, options, start_time
            )
        else:
            response = await self._ollama.chat(
                model=model,
                messages=formatted_messages,
                options=options,
                stream=False,
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract usage (Ollama provides this in non-streaming)
            prompt_tokens = response.get("prompt_eval_count", 0)
            completion_tokens = response.get("eval_count", 0)
            
            return GenerationResult(
                text=response.get("message", {}).get("content", ""),
                model=model,
                provider="ollama",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                generation_time_ms=generation_time_ms,
                finish_reason=response.get("done_reason", "stop"),
            )
    
    async def _stream_generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any],
        start_time: float,
    ) -> AsyncGenerator[StreamingChunk, None]:
        if not self._ollama:
            raise RuntimeError("Ollama not initialized")
        
        first_token_time = None
        accumulated_text = ""
        
        async for chunk in self._ollama.chat(
            model=model,
            messages=messages,
            options=options,
            stream=True,
        ):
            if not first_token_time:
                first_token_time = int((time.time() - start_time) * 1000)
            
            content = chunk.get("message", {}).get("content", "")
            if content:
                accumulated_text += content
            
            is_final = chunk.get("done", False)
            finish_reason = chunk.get("done_reason") if is_final else None
            
            usage = None
            if is_final:
                usage = {
                    "prompt_tokens": chunk.get("prompt_eval_count", 0),
                    "completion_tokens": chunk.get("eval_count", 0),
                }
            
            yield StreamingChunk(
                text=content,
                is_final=is_final,
                finish_reason=finish_reason,
                usage=usage,
            )
    
    async def generate_with_timing(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> GenerationResult:
        """Generate with detailed timing."""
        return await self.generate(model, messages, stream=False, **kwargs)
    
    async def embed(self, model: str, text: str) -> List[float]:
        """Generate embeddings."""
        if not self._ollama:
            raise RuntimeError("Inference engine not initialized")
        return await self._ollama.embeddings(model, text)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        ollama_healthy = False
        models = []
        
        if self._ollama:
            ollama_healthy = await self._ollama.health_check()
            if ollama_healthy:
                models = await self._ollama.list_models()
        
        return {
            "ollama": "healthy" if ollama_healthy else "unhealthy",
            "models_count": len(models),
            "models": [m["name"] for m in models],
        }


# Singleton
_inference_engine: Optional[InferenceEngine] = None
_engine_lock = asyncio.Lock()


async def get_inference_engine() -> InferenceEngine:
    global _inference_engine
    async with _engine_lock:
        if _inference_engine is None:
            _inference_engine = InferenceEngine()
            await _inference_engine.initialize()
        return _inference_engine


async def close_inference_engine() -> None:
    global _inference_engine
    async with _engine_lock:
        if _inference_engine:
            if _inference_engine._ollama:
                await _inference_engine._ollama.close()
            _inference_engine = None