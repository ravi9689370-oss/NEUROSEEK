"""Ollama client for model inference."""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, List, Optional, Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class OllamaClient:
    """Async client for Ollama API."""
    
    def __init__(self, host: Optional[str] = None, timeout: Optional[int] = None):
        self.host = host or settings.ollama.host
        self.timeout = timeout or settings.ollama.timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=settings.ollama.max_parallel),
            )
        return self._client
    
    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    # Model management
    async def list_models(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])
    
    async def pull_model(self, name: str, stream: bool = True) -> AsyncGenerator[Dict, None]:
        client = await self._get_client()
        async with client.stream(
            "POST", "/api/pull", json={"name": name, "stream": stream}
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)
    
    async def delete_model(self, name: str) -> bool:
        client = await self._get_client()
        response = await client.delete("/api/delete", json={"name": name})
        return response.status_code == 200
    
    async def show_model_info(self, name: str) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.post("/api/show", json={"name": name})
        response.raise_for_status()
        return response.json()
    
    # Inference
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None] | Dict[str, Any]:
        client = await self._get_client()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        
        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        if options:
            payload["options"] = options
        
        if stream:
            return self._stream_generate(client, payload)
        else:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json()
    
    async def _stream_generate(
        self, client: httpx.AsyncClient, payload: Dict
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None] | Dict[str, Any]:
        client = await self._get_client()
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        if options:
            payload["options"] = options
        
        if stream:
            return self._stream_chat(client, payload)
        else:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
    
    async def _stream_chat(
        self, client: httpx.AsyncClient, payload: Dict
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)
    
    async def embeddings(self, model: str, prompt: str) -> List[float]:
        client = await self._get_client()
        response = await client.post("/api/embeddings", json={"model": model, "prompt": prompt})
        response.raise_for_status()
        return response.json().get("embedding", [])
    
    async def copy_model(self, source: str, destination: str) -> bool:
        client = await self._get_client()
        response = await client.post("/api/copy", json={"source": source, "destination": destination})
        return response.status_code == 200
    
    async def create_model(self, name: str, modelfile: str) -> bool:
        client = await self._get_client()
        response = await client.post("/api/create", json={"name": name, "modelfile": modelfile})
        return response.status_code == 200
    
    # Health
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/")
            return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


async def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def close_ollama_client() -> None:
    global _ollama_client
    if _ollama_client:
        await _ollama_client.close()
        _ollama_client = None