"""Smart model routing based on query intent and model capabilities."""
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import structlog

from app.core.config import get_settings
from app.services.inference.engine import InferenceEngine, get_inference_engine

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RoutingDecision:
    model: str
    intent: str
    confidence: float
    reasoning: str
    alternatives: List[str]


class IntentClassifier:
    """Classify query intent using a lightweight model or rules."""
    
    INTENT_KEYWORDS = {
        "coding": [
            r"\b(code|program|function|class|api|debug|error|bug|implement|script|algorithm|database|sql|query)\b",
            r"\b(python|javascript|typescript|rust|go|java|c\+\+|react|vue|django|fastapi|node)\b",
            r"\b(git|docker|kubernetes|aws|gcp|azure|ci/cd|pipeline)\b",
        ],
        "reasoning": [
            r"\b(why|how|explain|analyze|reason|logic|proof|deduce|infer|conclude)\b",
            r"\b(step by step|think through|break down|compare|contrast|evaluate)\b",
            r"\b(math|mathematics|calculate|solve|equation|formula)\b",
        ],
        "creative": [
            r"\b(write|create|story|poem|creative|imagine|brainstorm|idea)\b",
            r"\b(joke|humor|funny|entertain|fiction|narrative)\b",
        ],
        "analysis": [
            r"\b(analyze|review|critique|assess|evaluate|summarize|synthesize)\b",
            r"\b(data|report|document|paper|article|research)\b",
        ],
        "fast": [
            r"^(what|who|when|where|which|define|meaning)\b",
            r"\b(quick|brief|short|simple)\b",
        ],
    }
    
    def __init__(self, engine: Optional[InferenceEngine] = None):
        self.engine = engine
        self.classifier_model = settings.inference.routing.intent_classifier_model
        self._compiled_patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in self.INTENT_KEYWORDS.items()
        }
    
    async def classify(self, query: str, context: Optional[List[Dict]] = None) -> Dict[str, float]:
        """Classify query intent, returns scores for each intent."""
        # Try rule-based first (fast)
        rule_scores = self._rule_based_classify(query)
        
        # If we have a classifier model and confidence is low, use LLM
        max_score = max(rule_scores.values()) if rule_scores else 0
        if max_score < 0.6 and self.engine:
            try:
                llm_scores = await self._llm_classify(query, context)
                # Blend scores
                return {k: (rule_scores.get(k, 0) + llm_scores.get(k, 0)) / 2 
                        for k in set(rule_scores) | set(llm_scores)}
            except Exception as e:
                logger.warning("llm_classification_failed", error=str(e))
        
        return rule_scores
    
    def _rule_based_classify(self, query: str) -> Dict[str, float]:
        scores = {}
        query_lower = query.lower()
        
        for intent, patterns in self._compiled_patterns.items():
            matches = sum(1 for p in patterns if p.search(query))
            if matches > 0:
                scores[intent] = min(0.9, 0.3 + matches * 0.2)
        
        # Default to general if no matches
        if not scores:
            scores["general"] = 0.5
        
        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores
    
    async def _llm_classify(self, query: str, context: Optional[List[Dict]] = None) -> Dict[str, float]:
        """Use LLM for intent classification."""
        system_prompt = """Classify the user's query into one or more intents. 
Return a JSON object with intent scores (0-1).
Intents: coding, reasoning, creative, analysis, fast, general

Examples:
- "Write a Python function to sort a list" -> {"coding": 0.9, "general": 0.1}
- "Why is the sky blue?" -> {"reasoning": 0.7, "analysis": 0.3}
- "Tell me a joke" -> {"creative": 0.8, "general": 0.2}

Query: {query}
Return ONLY the JSON object:"""
        
        messages = [
            {"role": "system", "content": system_prompt.format(query=query)},
        ]
        
        if context:
            # Add last few messages as context
            for msg in context[-3:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        response = await self.engine.generate(
            model=self.classifier_model,
            messages=messages,
            temperature=0.1,
            max_tokens=100,
        )
        
        try:
            result = json.loads(response.text.strip())
            return {k: float(v) for k, v in result.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, ValueError):
            return {"general": 0.5}


class ModelRouter:
    """Route queries to the best model based on intent and availability."""
    
    def __init__(self, engine: Optional[InferenceEngine] = None):
        self.engine = engine
        self.classifier = IntentClassifier(engine)
        self.routing_rules = settings.inference.routing.rules
        self.fallback_model = settings.inference.routing.fallback_model
    
    async def route(
        self,
        query: str,
        context: Optional[List[Dict]] = None,
        preferred_model: Optional[str] = None,
    ) -> RoutingDecision:
        """Route query to best model."""
        # If user specified model, use it (with validation)
        if preferred_model:
            available = await self.engine.is_model_available(preferred_model)
            if available:
                return RoutingDecision(
                    model=preferred_model,
                    intent="user_specified",
                    confidence=1.0,
                    reasoning="User explicitly requested this model",
                    alternatives=[],
                )
            else:
                logger.warning("preferred_model_unavailable", model=preferred_model)
        
        # Classify intent
        intent_scores = await self.classifier.classify(query, context)
        primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[primary_intent]
        
        # Get candidate models for intent
        candidates = self.routing_rules.get(primary_intent, self.routing_rules.get("general", []))
        
        # Filter to available models
        available_models = []
        for model in candidates:
            if await self.engine.is_model_available(model):
                available_models.append(model)
        
        if not available_models:
            # Fallback
            available_models = [self.fallback_model]
            if not await self.engine.is_model_available(self.fallback_model):
                # Last resort - any available model
                all_models = await self.engine.list_models()
                if all_models:
                    available_models = [all_models[0]["name"]]
                else:
                    raise RuntimeError("No models available")
        
        selected = available_models[0]
        alternatives = available_models[1:3]
        
        reasoning = f"Intent: {primary_intent} (confidence: {confidence:.2f}). Selected from {len(available_models)} available models."
        
        return RoutingDecision(
            model=selected,
            intent=primary_intent,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
        )
    
    async def get_routing_info(self, query: str, context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Get detailed routing information for debugging/UI."""
        intent_scores = await self.classifier.classify(query, context)
        primary_intent = max(intent_scores, key=intent_scores.get)
        candidates = self.routing_rules.get(primary_intent, self.routing_rules.get("general", []))
        
        availability = {}
        for model in candidates:
            availability[model] = await self.engine.is_model_available(model)
        
        return {
            "intent_scores": intent_scores,
            "primary_intent": primary_intent,
            "candidate_models": candidates,
            "availability": availability,
            "routing_rules": self.routing_rules,
        }


# Singleton
_model_router: Optional[ModelRouter] = None
_router_lock = asyncio.Lock()


async def get_model_router() -> ModelRouter:
    global _model_router
    async with _router_lock:
        if _model_router is None:
            engine = await get_inference_engine()
            _model_router = ModelRouter(engine)
        return _model_router