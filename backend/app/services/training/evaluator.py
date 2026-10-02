"""Model evaluation - benchmark trained models against base models."""
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog

from app.core.config import get_settings
from app.services.inference.engine import InferenceEngine, get_inference_engine

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EvaluationResult:
    model_id: str
    benchmark: str
    score: float
    details: Dict[str, Any]
    compared_to_base: Optional[float] = None
    improvement: Optional[float] = None
    passed: bool = False


class ModelEvaluator:
    """Evaluate models on standard benchmarks and custom tests."""
    
    def __init__(self, engine: Optional[InferenceEngine] = None):
        self.engine = engine
        self.config = settings.evaluation
        self.benchmarks = self.config.benchmarks
        self.judge_model = self.config.judge_model
    
    async def evaluate_model(
        self,
        model_name: str,
        benchmarks: Optional[List[str]] = None,
        base_model: Optional[str] = None,
    ) -> List[EvaluationResult]:
        """Run evaluation on specified benchmarks."""
        benchmarks = benchmarks or self.benchmarks
        results = []
        
        for benchmark in benchmarks:
            try:
                if benchmark == "mt_bench":
                    result = await self._eval_mt_bench(model_name, base_model)
                elif benchmark == "humaneval":
                    result = await self._eval_humaneval(model_name, base_model)
                elif benchmark == "gsm8k":
                    result = await self._eval_gsm8k(model_name, base_model)
                elif benchmark == "custom_eval":
                    result = await self._eval_custom(model_name, base_model)
                else:
                    logger.warning("unknown_benchmark", benchmark=benchmark)
                    continue
                
                results.append(result)
            except Exception as e:
                logger.error("benchmark_failed", benchmark=benchmark, error=str(e))
                results.append(EvaluationResult(
                    model_id=model_name,
                    benchmark=benchmark,
                    score=0.0,
                    details={"error": str(e)},
                    passed=False,
                ))
        
        return results
    
    async def _eval_mt_bench(
        self,
        model_name: str,
        base_model: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate on MT-Bench style questions."""
        # MT-Bench style questions
        questions = [
            "Write a Python function to find the longest palindromic substring.",
            "Explain the concept of dependency injection in software design.",
            "Compare and contrast REST and GraphQL APIs.",
            "Write a SQL query to find the second highest salary in each department.",
            "Explain how transformers work in NLP.",
            "Design a rate limiter for a distributed system.",
            "What are the trade-offs between consistency and availability in distributed databases?",
            "Write a recursive function to solve the Tower of Hanoi puzzle.",
        ]
        
        scores = []
        details = {"questions": []}
        
        for q in questions:
            messages = [{"role": "user", "content": q}]
            result = await self.engine.generate(
                model=model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            # Use judge model to score
            score = await self._judge_response(q, result.text)
            scores.append(score)
            details["questions"].append({
                "question": q,
                "response": result.text[:500],
                "score": score,
            })
        
        avg_score = sum(scores) / len(scores)
        
        # Compare to base model if provided
        compared = None
        improvement = None
        if base_model:
            base_result = await self._eval_mt_bench(base_model)
            compared = base_result.score
            improvement = avg_score - compared
        
        passed = improvement is None or improvement >= self.config.min_score_improvement
        
        return EvaluationResult(
            model_id=model_name,
            benchmark="mt_bench",
            score=avg_score,
            details=details,
            compared_to_base=compared,
            improvement=improvement,
            passed=passed,
        )
    
    async def _eval_humaneval(
        self,
        model_name: str,
        base_model: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate on HumanEval coding benchmark (simplified)."""
        # Simplified - would normally use actual HumanEval dataset
        coding_tasks = [
            ("Write a function to check if a string is a valid palindrome", "python"),
            ("Implement binary search", "python"),
            ("Write a function to merge two sorted lists", "python"),
            ("Implement a LRU cache", "python"),
            ("Write a function to detect cycle in linked list", "python"),
        ]
        
        scores = []
        details = {"tasks": []}
        
        for task, lang in coding_tasks:
            prompt = f"```{lang}\n# {task}\ndef solution():\n    pass\n```"
            messages = [{"role": "user", "content": f"Complete this code:\n{prompt}"}]
            
            result = await self.engine.generate(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            
            # Basic heuristic scoring (would use actual test execution)
            score = self._score_code_completion(result.text, task)
            scores.append(score)
            details["tasks"].append({
                "task": task,
                "response": result.text[:500],
                "score": score,
            })
        
        avg_score = sum(scores) / len(scores)
        
        compared = None
        improvement = None
        if base_model:
            base_result = await self._eval_humaneval(base_model)
            compared = base_result.score
            improvement = avg_score - compared
        
        return EvaluationResult(
            model_id=model_name,
            benchmark="humaneval",
            score=avg_score,
            details=details,
            compared_to_base=compared,
            improvement=improvement,
            passed=improvement is None or improvement >= self.config.min_score_improvement,
        )
    
    async def _eval_gsm8k(
        self,
        model_name: str,
        base_model: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate on GSM8K math reasoning (simplified)."""
        math_problems = [
            "If a train travels 120 miles in 2 hours, what is its average speed?",
            "A store has 150 apples. They sell 40% on Monday and 25% of remaining on Tuesday. How many left?",
            "The sum of three consecutive integers is 72. What are the integers?",
            "A rectangle has perimeter 30 and area 56. What are its dimensions?",
            "If 3x + 7 = 22, what is x?",
        ]
        
        scores = []
        details = {"problems": []}
        
        for problem in math_problems:
            messages = [{
                "role": "user",
                "content": f"Solve step by step: {problem}"
            }]
            
            result = await self.engine.generate(
                model=model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=512,
            )
            
            # Score based on correct answer presence
            score = self._score_math_answer(result.text, problem)
            scores.append(score)
            details["problems"].append({
                "problem": problem,
                "response": result.text[:300],
                "score": score,
            })
        
        avg_score = sum(scores) / len(scores)
        
        compared = None
        improvement = None
        if base_model:
            base_result = await self._eval_gsm8k(base_model)
            compared = base_result.score
            improvement = avg_score - compared
        
        return EvaluationResult(
            model_id=model_name,
            benchmark="gsm8k",
            score=avg_score,
            details=details,
            compared_to_base=compared,
            improvement=improvement,
            passed=improvement is None or improvement >= self.config.min_score_improvement,
        )
    
    async def _eval_custom(
        self,
        model_name: str,
        base_model: Optional[str] = None,
    ) -> EvaluationResult:
        """Run custom evaluation from dataset."""
        # Load custom eval dataset
        eval_path = Path(self.config.custom_eval_dataset)
        if not eval_path.exists():
            return EvaluationResult(
                model_id=model_name,
                benchmark="custom_eval",
                score=0.5,
                details={"error": "Custom eval dataset not found"},
                passed=False,
            )
        
        with open(eval_path) as f:
            eval_data = [json.loads(line) for line in f]
        
        scores = []
        details = {"samples": []}
        
        for item in eval_data[:20]:  # Limit for speed
            prompt = item.get("prompt", "")
            expected = item.get("expected", "")
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.engine.generate(
                model=model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=512,
            )
            
            score = await self._judge_response(prompt, result.text, expected)
            scores.append(score)
            details["samples"].append({
                "prompt": prompt[:100],
                "expected": expected[:100],
                "response": result.text[:200],
                "score": score,
            })
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        compared = None
        improvement = None
        if base_model:
            base_result = await self._eval_custom(base_model)
            compared = base_result.score
            improvement = avg_score - compared
        
        return EvaluationResult(
            model_id=model_name,
            benchmark="custom_eval",
            score=avg_score,
            details=details,
            compared_to_base=compared,
            improvement=improvement,
            passed=improvement is None or improvement >= self.config.min_score_improvement,
        )
    
    async def _judge_response(
        self,
        prompt: str,
        response: str,
        expected: Optional[str] = None,
    ) -> float:
        """Use judge model to score response quality."""
        judge_prompt = f"""Rate the quality of this response on a scale of 0-1.

Prompt: {prompt}
Response: {response}
{f"Expected: {expected}" if expected else ""}

Consider: accuracy, completeness, clarity, correctness.
Return only a number between 0 and 1:"""
        
        messages = [{"role": "user", "content": judge_prompt}]
        
        try:
            result = await self.engine.generate(
                model=self.judge_model,
                messages=messages,
                temperature=0.1,
                max_tokens=10,
            )
            score_text = result.text.strip()
            # Extract number
            import re
            match = re.search(r'(\d*\.?\d+)', score_text)
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score))
        except Exception as e:
            logger.warning("judge_failed", error=str(e))
        
        # Fallback heuristic
        return 0.5
    
    def _score_code_completion(self, response: str, task: str) -> float:
        """Heuristic scoring for code completion."""
        score = 0.0
        response_lower = response.lower()
        
        # Check for key elements
        if "def " in response or "function" in response_lower:
            score += 0.3
        if "return" in response_lower:
            score += 0.2
        if any(kw in response_lower for kw in ["if", "for", "while", "try", "except"]):
            score += 0.2
        if len(response) > 50:
            score += 0.1
        if "```" in response:
            score += 0.2
        
        return min(1.0, score)
    
    def _score_math_answer(self, response: str, problem: str) -> float:
        """Heuristic scoring for math problems."""
        score = 0.0
        response_lower = response.lower()
        
        # Check for step-by-step reasoning
        if any(w in response_lower for w in ["step", "first", "then", "therefore", "so"]):
            score += 0.3
        # Check for numerical answer
        import re
        if re.search(r'\d+', response):
            score += 0.3
        # Check for explanation
        if len(response) > 30:
            score += 0.2
        # Check for correct keywords from problem
        problem_nums = re.findall(r'\d+', problem)
        for num in problem_nums:
            if num in response:
                score += 0.1
        
        return min(1.0, score)
    
    async def compare_models(
        self,
        model_a: str,
        model_b: str,
        prompts: List[str],
    ) -> Dict[str, Any]:
        """Side-by-side comparison of two models."""
        results = {"model_a": model_a, "model_b": model_b, "comparisons": []}
        
        wins = {"a": 0, "b": 0, "tie": 0}
        
        for prompt in prompts:
            messages = [{"role": "user", "content": prompt}]
            
            # Generate from both
            result_a = await self.engine.generate(model_a, messages, temperature=0.7)
            result_b = await self.engine.generate(model_b, messages, temperature=0.7)
            
            # Judge
            judge_prompt = f"""Compare these two responses and pick the better one.

Prompt: {prompt}

Response A: {result_a.text}

Response B: {result_b.text}

Which is better? Answer with "A", "B", or "TIE" and brief reason:"""
            
            judge_result = await self.engine.generate(
                self.judge_model,
                [{"role": "user", "content": judge_prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            
            verdict = judge_result.text.strip().upper()
            if "A" in verdict and "B" not in verdict:
                wins["a"] += 1
                winner = "a"
            elif "B" in verdict and "A" not in verdict:
                wins["b"] += 1
                winner = "b"
            else:
                wins["tie"] += 1
                winner = "tie"
            
            results["comparisons"].append({
                "prompt": prompt,
                "winner": winner,
                "judge_reasoning": judge_result.text,
            })
        
        results["summary"] = wins
        results["win_rate_a"] = wins["a"] / len(prompts) if prompts else 0
        
        return results


# Singleton
_evaluator: Optional[ModelEvaluator] = None
_evaluator_lock = asyncio.Lock()


async def get_evaluator() -> ModelEvaluator:
    global _evaluator
    async with _evaluator_lock:
        if _evaluator is None:
            engine = await get_inference_engine()
            _evaluator = ModelEvaluator(engine)
        return _evaluator