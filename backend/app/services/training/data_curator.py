"""Data curation for training - collect, filter, and prepare datasets from conversations."""
import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import structlog
from datasets import Dataset, DatasetDict
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.conversation import Conversation, Message, MessageRole, MessageFeedback
from app.models.training import TrainingRun

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class CurationStats:
    total_conversations: int
    eligible_conversations: int
    positive_samples: int
    negative_samples: int
    edited_samples: int
    preference_pairs: int
    sft_samples: int
    deduplicated: int


class DataCurator:
    """Curate training data from user conversations and feedback."""
    
    def __init__(self):
        self.config = settings.data.curation
        self.splits = settings.data.splits
    
    async def curate_training_data(
        self,
        since: Optional[datetime] = None,
        min_quality: Optional[float] = None,
    ) -> Tuple[DatasetDict, CurationStats]:
        """Main entry point - curate all training data."""
        async with get_db_session() as db:
            # Get eligible conversations
            conversations = await self._get_eligible_conversations(db, since)
            
            stats = CurationStats(
                total_conversations=0,
                eligible_conversations=len(conversations),
                positive_samples=0,
                negative_samples=0,
                edited_samples=0,
                preference_pairs=0,
                sft_samples=0,
                deduplicated=0,
            )
            
            # Extract different types of training data
            preference_pairs = await self._extract_preference_pairs(db, conversations)
            stats.preference_pairs = len(preference_pairs)
            
            sft_samples = await self._extract_sft_samples(db, conversations)
            stats.sft_samples = len(sft_samples)
            
            # Count feedback types
            for conv in conversations:
                for msg in conv.messages:
                    if msg.feedback == MessageFeedback.POSITIVE:
                        stats.positive_samples += 1
                    elif msg.feedback == MessageFeedback.NEGATIVE:
                        stats.negative_samples += 1
                    elif msg.feedback == MessageFeedback.EDITED:
                        stats.edited_samples += 1
            
            # Deduplicate
            preference_pairs = self._deduplicate_pairs(preference_pairs)
            sft_samples = self._deduplicate_sft(sft_samples)
            stats.deduplicated = len(preference_pairs) + len(sft_samples)
            
            # Create datasets
            dataset_dict = self._create_datasets(preference_pairs, sft_samples)
            
            logger.info("data_curation_completed", stats=stats.__dict__)
            return dataset_dict, stats
    
    async def _get_eligible_conversations(
        self,
        db: AsyncSession,
        since: Optional[datetime] = None,
    ) -> List[Conversation]:
        """Get conversations eligible for training."""
        cutoff = since or (datetime.now(timezone.utc) - timedelta(days=self.config.max_conversation_age_days))
        
        query = select(Conversation).where(
            and_(
                Conversation.created_at >= cutoff,
                Conversation.is_archived == False,
            )
        ).order_by(Conversation.created_at.desc())
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        # Filter by minimum length
        eligible = [
            c for c in conversations
            if len(c.messages) >= self.config.min_conversation_length
        ]
        
        return eligible
    
    async def _extract_preference_pairs(
        self,
        db: AsyncSession,
        conversations: List[Conversation],
    ) -> List[Dict[str, Any]]:
        """Extract preference pairs (chosen vs rejected) for DPO training."""
        pairs = []
        
        for conv in conversations:
            messages = sorted(conv.messages, key=lambda m: m.created_at)
            
            for i, msg in enumerate(messages):
                if msg.role != MessageRole.ASSISTANT:
                    continue
                
                # Case 1: Explicit positive/negative feedback
                if msg.feedback == MessageFeedback.POSITIVE:
                    # Find a negative example for same/similar context
                    negative = await self._find_negative_counterpart(db, msg, conv)
                    if negative:
                        pairs.append({
                            "prompt": self._format_prompt(messages[:i]),
                            "chosen": msg.content,
                            "rejected": negative.content,
                            "source": "explicit_feedback",
                            "conversation_id": str(conv.id),
                            "chosen_message_id": str(msg.id),
                            "rejected_message_id": str(negative.id),
                        })
                
                # Case 2: User edited the response
                elif msg.feedback == MessageFeedback.EDITED and msg.metadata.get("original_content"):
                    pairs.append({
                        "prompt": self._format_prompt(messages[:i]),
                        "chosen": msg.content,  # User's edited version
                        "rejected": msg.metadata["original_content"],  # Model's original
                        "source": "user_edit",
                        "conversation_id": str(conv.id),
                        "chosen_message_id": str(msg.id),
                        "rejected_message_id": str(msg.id),
                    })
                
                # Case 3: Regenerated - compare first vs last attempt
                elif msg.feedback == MessageFeedback.REGENERATED:
                    prev_attempts = [
                        m for m in messages[:i]
                        if m.role == MessageRole.ASSISTANT
                        and m.metadata.get("generation_attempt", 0) < msg.metadata.get("generation_attempt", 1)
                    ]
                    if prev_attempts:
                        # Assume last attempt is preferred (user kept regenerating)
                        pairs.append({
                            "prompt": self._format_prompt(messages[:i]),
                            "chosen": msg.content,
                            "rejected": prev_attempts[-1].content,
                            "source": "regeneration",
                            "conversation_id": str(conv.id),
                            "chosen_message_id": str(msg.id),
                            "rejected_message_id": str(prev_attempts[-1].id),
                        })
        
        return pairs
    
    async def _find_negative_counterpart(
        self,
        db: AsyncSession,
        positive_msg: Message,
        conversation: Conversation,
    ) -> Optional[Message]:
        """Find a negatively-rated response for similar context."""
        # Look for negative feedback in same conversation
        for msg in conversation.messages:
            if (msg.role == MessageRole.ASSISTANT 
                and msg.feedback == MessageFeedback.NEGATIVE
                and msg.id != positive_msg.id):
                return msg
        
        # Could expand to cross-conversation similarity search using embeddings
        return None
    
    async def _extract_sft_samples(
        self,
        db: AsyncSession,
        conversations: List[Conversation],
    ) -> List[Dict[str, Any]]:
        """Extract supervised fine-tuning samples (high-quality assistant responses)."""
        samples = []
        
        for conv in conversations:
            messages = sorted(conv.messages, key=lambda m: m.created_at)
            
            for i, msg in enumerate(messages):
                if msg.role != MessageRole.ASSISTANT:
                    continue
                
                # Include if positive feedback or high-quality indicators
                include = False
                quality_score = 0.0
                
                if msg.feedback == MessageFeedback.POSITIVE:
                    include = True
                    quality_score = 1.0
                elif msg.feedback is None and msg.is_training_candidate:
                    include = True
                    quality_score = msg.training_weight
                elif msg.generation_time_ms and msg.generation_time_ms > 1000:
                    # Longer generation might indicate more thoughtful response
                    include = True
                    quality_score = 0.5
                
                if include and quality_score >= (self.config.preference_threshold or 0.5):
                    # Format as conversation for SFT
                    prompt_messages = messages[:i]
                    prompt_messages.append({"role": "assistant", "content": msg.content})
                    
                    text = self._format_conversation_for_sft(prompt_messages)
                    
                    samples.append({
                        "text": text,
                        "quality_score": quality_score,
                        "source": "sft",
                        "conversation_id": str(conv.id),
                        "message_id": str(msg.id),
                        "model": msg.model,
                    })
        
        return samples
    
    def _format_prompt(self, messages: List[Message]) -> str:
        """Format messages as a prompt string."""
        formatted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                formatted.append(f"<|system|>\n{msg.content}")
            elif msg.role == MessageRole.USER:
                formatted.append(f"<|user|>\n{msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                formatted.append(f"<|assistant|>\n{msg.content}")
        return "\n".join(formatted)
    
    def _format_conversation_for_sft(self, messages: List[Dict]) -> str:
        """Format full conversation for SFT training."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(f"<|system|>\n{content}")
            elif role == "user":
                formatted.append(f"<|user|>\n{content}")
            elif role == "assistant":
                formatted.append(f"<|assistant|>\n{content}")
        return "\n".join(formatted) + "<|endoftext|>"
    
    def _deduplicate_pairs(self, pairs: List[Dict]) -> List[Dict]:
        """Remove duplicate preference pairs based on content similarity."""
        seen = set()
        unique = []
        
        for pair in pairs:
            # Create hash of prompt + chosen
            content_hash = hashlib.md5(
                (pair["prompt"] + pair["chosen"]).encode()
            ).hexdigest()[:16]
            
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(pair)
        
        return unique
    
    def _deduplicate_sft(self, samples: List[Dict]) -> List[Dict]:
        """Remove duplicate SFT samples."""
        seen = set()
        unique = []
        
        for sample in samples:
            content_hash = hashlib.md5(sample["text"].encode()).hexdigest()[:16]
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(sample)
        
        return unique
    
    def _create_datasets(
        self,
        preference_pairs: List[Dict],
        sft_samples: List[Dict],
    ) -> DatasetDict:
        """Create HuggingFace DatasetDict with train/val/test splits."""
        datasets = {}
        
        # Preference dataset for DPO
        if preference_pairs:
            pref_ds = Dataset.from_list(preference_pairs)
            datasets["preference"] = pref_ds.train_test_split(
                test_size=1 - self.splits["train"],
                seed=42,
            )
        
        # SFT dataset
        if sft_samples:
            sft_ds = Dataset.from_list(sft_samples)
            datasets["sft"] = sft_ds.train_test_split(
                test_size=1 - self.splits["train"],
                seed=42,
            )
        
        # Further split test into val/test
        for key in datasets:
            if "test" in datasets[key]:
                test_split = datasets[key]["test"].train_test_split(
                    test_size=self.splits["test"] / (self.splits["validation"] + self.splits["test"]),
                    seed=42,
                )
                datasets[key]["validation"] = test_split["train"]
                datasets[key]["test"] = test_split["test"]
                del datasets[key]["test"]  # Will be recreated above
        
        return DatasetDict(datasets)
    
    async def save_datasets(
        self,
        dataset_dict: DatasetDict,
        output_dir: str,
    ) -> Dict[str, str]:
        """Save datasets to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_paths = {}
        
        for split_name, dataset in dataset_dict.items():
            if isinstance(dataset, DatasetDict):
                for sub_split, sub_dataset in dataset.items():
                    file_path = output_path / f"{split_name}_{sub_split}.jsonl"
                    sub_dataset.to_json(file_path)
                    saved_paths[f"{split_name}_{sub_split}"] = str(file_path)
            else:
                file_path = output_path / f"{split_name}.jsonl"
                dataset.to_json(file_path)
                saved_paths[split_name] = str(file_path)
        
        # Save metadata
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "splits": {k: len(v) if hasattr(v, '__len__') else {sk: len(sv) for sk, sv in v.items()} 
                      for k, v in dataset_dict.items()},
            "config": {
                "min_conversation_length": self.config.min_conversation_length,
                "preference_threshold": self.config.preference_threshold,
            }
        }
        
        meta_path = output_path / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return saved_paths


# Singleton
_data_curator: Optional[DataCurator] = None
_curator_lock = asyncio.Lock()


async def get_data_curator() -> DataCurator:
    global _data_curator
    async with _curator_lock:
        if _data_curator is None:
            _data_curator = DataCurator()
        return _data_curator