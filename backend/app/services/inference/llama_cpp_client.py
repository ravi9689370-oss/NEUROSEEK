"""llama.cpp client for direct model inference (fallback/alternative to Ollama)."""
import asyncio
import time
from typing import AsyncGenerator, Dict, List, Optional, Any

import structlog
from llama_cpp import Llama

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class LlamaCppClient:
    """Direct llama.cpp inference client."""
    
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        n_threads: Optional[int] = None,
        verbose: bool = False,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self.n_threads = n_threads
        self.verbose = verbose
        self._llm: Optional[Llama] = None
        self._lock = asyncio.Lock()
    
    async def load(self) -> None:
        """Load model in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        async with self._lock:
            if self._llm is None:
                self._llm = await loop.run_in_executor(
                    None,
                    self._create_llama,
                )
                logger.info("llama_cpp_model_loaded", model=self.model_path)
    
    def _create_llama(self) -> Llama:
        return Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_batch=self.n_batch,
            n_threads=self.n_threads,
            verbose=self.verbose,
            use_mmap=True,
            use_mlock=False,
        )
    
    async def unload(self) -> None:
        async with self._lock:
            if self._llm:
                del self._llm
                self._llm = None
    
    def _generate_sync(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        return self._llm(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            stop=stop,
            stream=stream,
        )
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        await self.load()
        
        loop = asyncio.get_event_loop()
        
        if stream:
            return self._stream_generate(
                prompt, max_tokens, temperature, top_p, top_k, repeat_penalty, stop
            )
        else:
            return await loop.run_in_executor(
                None,
                self._generate_sync,
                prompt, max_tokens, temperature, top_p, top_k, repeat_penalty, stop, False
            )
    
    async def _stream_generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        repeat_penalty: float,
        stop: Optional[List[str]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        loop = asyncio.get_event_loop()
        
        # Run streaming in executor
        generator = await loop.run_in_executor(
            None,
            self._generate_sync,
            prompt, max_tokens, temperature, top_p, top_k, repeat_penalty, stop, True
        )
        
        for chunk in generator:
            yield chunk
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        await self.load()
        
        loop = asyncio.get_event_loop()
        
        if stream:
            return self._stream_chat_completion(
                messages, max_tokens, temperature, top_p, top_k, repeat_penalty, stop
            )
        else:
            return await loop.run_in_executor(
                None,
                lambda: self._llm.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop=stop,
                    stream=False,
                )
            )
    
    async def _stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        repeat_penalty: float,
        stop: Optional[List[str]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        loop = asyncio.get_event_loop()
        
        generator = await loop.run_in_executor(
            None,
            lambda: self._llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stop=stop,
                stream=True,
            )
        )
        
        for chunk in generator:
            yield chunk
    
    def tokenize(self, text: str) -> List[int]:
        if self._llm is None:
            raise RuntimeError("Model not loaded")
        return self._llm.tokenize(text.encode())
    
    def detokenize(self, tokens: List[int]) -> str:
        if self._llm is None:
            raise RuntimeError("Model not loaded")
        return self._llm.detokenize(tokens).decode()
    
    @property
    def is_loaded(self) -> bool:
        return self._llm is not None


# Model cache
_llama_clients: Dict[str, LlamaCppClient] = {}
_cache_lock = asyncio.Lock()


async def get_llama_cpp_client(
    model_path: str,
    **kwargs
) -> LlamaCppClient:
    """Get or create llama.cpp client for model."""
    async with _cache_lock:
        if model_path not in _llama_clients:
            _llama_clients[model_path] = LlamaCppClient(model_path, **kwargs)
        return _llama_clients[model_path]


async def close_all_llama_clients() -> None:
    async with _cache_lock:
        for client in _llama_clients.values():
            await client.unload()
        _llama_clients.clear()