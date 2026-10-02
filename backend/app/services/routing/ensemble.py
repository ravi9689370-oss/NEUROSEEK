"""Ensemble inference - run multiple models and synthesize best answer."""
import asyncio
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, AsyncGenerator

import structlog

from app.core.config import get_settings
from app.services.inference.engine import InferenceEngine, get_inference_engine, GenerationResult, StreamingChunk

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EnsembleResult:
    synthesized_answer: str
    model_responses: Dict[str, GenerationResult]
    synthesis_model: str
    confidence: float
    total_time_ms: int


class EnsembleManager:
    """Manage multi-model ensemble inference."""
    
    def __init__(self, engine: Optional[InferenceEngine] = None):
        self.engine = engine
        self.ensemble_config = settings.inference.ensemble
        self.enabled = self.ensemble_config.enabled
        self.max_models = self.ensemble_config.max_models
        self.synthesis_model = self.ensemble_config.synthesis_model
        self.voting_strategy = self.ensemble_config.voting_strategy
        self.weights = self.ensemble_config.weights
    
    async def run_ensemble(
        self,
        messages: List[Dict[str, str]],
        models: Optional[List[str]] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> EnsembleResult | AsyncGenerator[Dict[str, Any], None]:
        """Run inference on multiple models and synthesize."""
        if not self.enabled:
            # Single model fallback
            model = models[0] if models else settings.ollama.default_model
            result = await self.engine.generate(model, messages, system, temperature, stream=False)
            return EnsembleResult(
                synthesized_answer=result.text,
                model_responses={model: result},
                synthesis_model=model,
                confidence=1.0,
                total_time_ms=result.generation_time_ms,
            )
        
        # Select models
        if models is None:
            models = self._select_models_for_query(messages)
        
        models = models[:self.max_models]
        
        # Run inference in parallel
        start_time = asyncio.get_event_loop().time()
        tasks = [
            self.engine.generate(
                model, messages, system, temperature, stream=False
            ) for model in models
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        model_responses = {}
        for model, result in zip(models, results):
            if isinstance(result, Exception):
                logger.warning("ensemble_model_failed", model=model, error=str(result))
            else:
                model_responses[model] = result
        
        if not model_responses:
            raise RuntimeError("All ensemble models failed")
        
        total_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Synthesize
        if len(model_responses) == 1:
            sole_result = next(iter(model_responses.values()))
            return EnsembleResult(
                synthesized_answer=sole_result.text,
                model_responses=model_responses,
                synthesis_model=sole_result.model,
                confidence=1.0,
                total_time_ms=total_time_ms,
            )
        
        synthesized = await self._synthesize_responses(
            messages[-1]["content"] if messages else "",
            model_responses,
        )
        
        return EnsembleResult(
            synthesized_answer=synthesized,
            model_responses=model_responses,
            synthesis_model=self.synthesis_model,
            confidence=0.9,  # Could compute from agreement
            total_time_ms=total_time_ms,
        )
    
    def _select_models_for_query(self, messages: List[Dict[str, str]]) -> List[str]:
        """Select diverse models for ensemble."""
        # Default diverse selection
        default_ensemble = [
            "llama3.1:8b",
            "qwen2.5-coder:7b",
            "nemotron3-ultra",
        ]
        
        # Filter to available (would need engine check, simplified here)
        return default_ensemble
    
    async def _synthesize_responses(
        self,
        query: str,
        responses: Dict[str, GenerationResult],
    ) -> str:
        """Synthesize multiple model responses into best answer."""
        # Format responses for synthesis
        formatted_responses = []
        for model, result in responses.items():
            weight = self.weights.get(model, 1.0)
            formatted_responses.append(
                f"--- Model: {model} (weight: {weight}) ---\n{result.text}"
            )
        
        responses_text = "\n\n".join(formatted_responses)
        
        synthesis_prompt = self.ensemble_config.synthesis_prompt.format(
            query=query,
            responses=responses_text,
        )
        
        messages = [
            {"role": "system", "content": "You are an expert answer synthesizer."},
            {"role": "user", "content": synthesis_prompt},
        ]
        
        try:
            result = await self.engine.generate(
                model=self.synthesis_model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            return result.text
        except Exception as e:
            logger.error("synthesis_failed", error=str(e))
            # Fallback: return highest weighted response
            best_model = max(responses.keys(), key=lambda m: self.weights.get(m, 1.0))
            return responses[best_model].text
    
    async def run_ensemble_stream(
        self,
        messages: List[Dict[str, str]],
        models: Optional[List[str]] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream ensemble results as they arrive."""
        if not self.enabled:
            model = models[0] if models else settings.ollama.default_model
            async for chunk in self.engine.generate(
                model, messages, system, temperature, stream=True
            ):
                yield {
                    "type": "token",
                    "model": model,
                    "text": chunk.text,
                    "is_final": chunk.is_final,
                }
            return
        
        if models is None:
            models = self._select_models_for_query(messages)
        
        models = models[:self.max_models]
        
        # Create tasks for each model
        queues: Dict[str, asyncio.Queue] = {m: asyncio.Queue() for m in models}
        
        async def run_model(model: str):
            try:
                async for chunk in self.engine.generate(
                    model, messages, system, temperature, stream=True
                ):
                    await queues[model].put({
                        "type": "token",
                        "model": model,
                        "text": chunk.text,
                        "is_final": chunk.is_final,
                        "usage": chunk.usage,
                    })
                await queues[model].put({"type": "done", "model": model})
            except Exception as e:
                await queues[model].put({"type": "error", "model": model, "error": str(e)})
        
        tasks = [asyncio.create_task(run_model(m)) for m in models]
        
        # Collect and yield tokens from all models
        completed = set()
        model_buffers: Dict[str, str] = {m: "" for m in models}
        
        while len(completed) < len(models):
            # Wait for any queue to have data
            done, pending = await asyncio.wait(
                [q.get() for q in queues.values()],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            for task in done:
                item = task.result()
                model = item["model"]
                
                if item["type"] == "token":
                    model_buffers[model] += item["text"]
                    yield item
                elif item["type"] == "done":
                    completed.add(model)
                elif item["type"] == "error":
                    logger.warning("ensemble_model_error", model=model, error=item["error"])
                    completed.add(model)
        
        # Cancel any remaining tasks
        for t in tasks:
            if not t.done():
                t.cancel()
        
        # Now synthesize
        if len(model_buffers) > 1:
            valid_responses = {
                m: GenerationResult(
                    text=buf, model=m, provider="ollama",
                    prompt_tokens=0, completion_tokens=0, total_tokens=0,
                    generation_time_ms=0
                )
                for m, buf in model_buffers.items() if buf
            }
            
            if valid_responses:
                synthesized = await self._synthesize_responses(
                    messages[-1]["content"] if messages else "",
                    valid_responses,
                )
                yield {
                    "type": "synthesis",
                    "text": synthesized,
                    "model": self.synthesis_model,
                }


# Singleton
_ensemble_manager: Optional[EnsembleManager] = None
_ensemble_lock = asyncio.Lock()


async def get_ensemble_manager() -> EnsembleManager:
    global _ensemble_manager
    async with _ensemble_lock:
        if _ensemble_manager is None:
            engine = await get_inference_engine()
            _ensemble_manager = EnsembleManager(engine)
        return _ensemble_manager