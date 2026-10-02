"""LoRA/QLoRA training with Unsloth optimization."""
import asyncio
import os
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog
import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer, DPOTrainer, DPOConfig

from app.core.config import get_settings
from app.services.inference.engine import get_inference_engine

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class TrainingResult:
    success: bool
    output_dir: str
    adapter_path: str
    metrics: Dict[str, Any]
    duration_seconds: int
    error: Optional[str] = None


class LoRATrainer:
    """High-performance LoRA/QLoRA trainer using Unsloth."""
    
    def __init__(self):
        self.config = settings.training
        self.unsloth_config = self.config.unsloth
        self.lora_config = self.config.lora
        self.trainer_config = self.config.trainer
        self.dpo_config = self.config.dpo
        self._model = None
        self._tokenizer = None
        self._ref_model = None
    
    async def train_lora(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
        output_dir: Optional[str] = None,
        run_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> TrainingResult:
        """Train LoRA adapters using SFT."""
        run_id = run_id or str(uuid.uuid4())[:8]
        output_dir = output_dir or f"models/adapters/lora_{run_id}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            # Load base model with Unsloth
            await self._load_model()
            
            # Configure training
            training_args = TrainingArguments(
                output_dir=output_dir,
                per_device_train_batch_size=self.trainer_config.per_device_train_batch_size,
                gradient_accumulation_steps=self.trainer_config.gradient_accumulation_steps,
                warmup_steps=self.trainer_config.warmup_steps,
                max_steps=self.trainer_config.max_steps,
                learning_rate=self.trainer_config.learning_rate,
                weight_decay=self.trainer_config.weight_decay,
                lr_scheduler_type=self.trainer_config.lr_scheduler_type,
                optim=self.trainer_config.optim,
                logging_steps=self.trainer_config.logging_steps,
                save_steps=self.trainer_config.save_steps,
                eval_steps=self.trainer_config.eval_steps,
                fp16=self.trainer_config.fp16,
                bf16=self.trainer_config.bf16,
                gradient_checkpointing=self.trainer_config.gradient_checkpointing,
                dataloader_num_workers=self.trainer_config.dataloader_num_workers,
                remove_unused_columns=self.trainer_config.remove_unused_columns,
                report_to="none",
                save_total_limit=3,
                load_best_model_at_end=eval_dataset is not None,
                metric_for_best_model="eval_loss",
                greater_is_better=False,
            )
            
            # Create trainer
            trainer = SFTTrainer(
                model=self._model,
                tokenizer=self._tokenizer,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                dataset_text_field="text",
                max_seq_length=self.unsloth_config.max_seq_length,
                args=training_args,
            )
            
            # Train with progress tracking
            if progress_callback:
                trainer.add_callback(ProgressCallback(progress_callback, run_id))
            
            # Run training in executor to avoid blocking
            loop = asyncio.get_event_loop()
            train_result = await loop.run_in_executor(None, trainer.train)
            
            # Save adapter
            adapter_path = f"{output_dir}/adapter"
            trainer.model.save_pretrained(adapter_path)
            self._tokenizer.save_pretrained(adapter_path)
            
            # Save training config
            config_path = f"{output_dir}/training_config.json"
            with open(config_path, "w") as f:
                json.dump({
                    "method": "lora",
                    "base_model": self.config.base_model,
                    "lora_config": {
                        "r": self.lora_config.r,
                        "alpha": self.lora_config.alpha,
                        "dropout": self.lora_config.dropout,
                        "target_modules": self.lora_config.target_modules,
                    },
                    "training_args": training_args.to_dict(),
                    "train_samples": len(train_dataset),
                    "eval_samples": len(eval_dataset) if eval_dataset else 0,
                }, f, indent=2)
            
            duration = int(time.time() - start_time)
            
            metrics = {
                "train_loss": train_result.training_loss,
                "train_steps": train_result.global_step,
                "epoch": train_result.epoch,
            }
            
            if eval_dataset:
                eval_result = await loop.run_in_executor(None, trainer.evaluate)
                metrics.update({
                    "eval_loss": eval_result.get("eval_loss"),
                    "eval_perplexity": eval_result.get("eval_perplexity"),
                })
            
            logger.info("lora_training_completed", run_id=run_id, duration=duration, metrics=metrics)
            
            return TrainingResult(
                success=True,
                output_dir=output_dir,
                adapter_path=adapter_path,
                metrics=metrics,
                duration_seconds=duration,
            )
            
        except Exception as e:
            logger.error("lora_training_failed", run_id=run_id, error=str(e))
            return TrainingResult(
                success=False,
                output_dir=output_dir,
                adapter_path="",
                metrics={},
                duration_seconds=int(time.time() - start_time),
                error=str(e),
            )
        finally:
            await self._cleanup()
    
    async def train_dpo(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
        output_dir: Optional[str] = None,
        run_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> TrainingResult:
        """Train using Direct Preference Optimization (DPO)."""
        run_id = run_id or str(uuid.uuid4())[:8]
        output_dir = output_dir or f"models/adapters/dpo_{run_id}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            # Load base model and reference model
            await self._load_model(load_ref=True)
            
            dpo_args = DPOConfig(
                output_dir=output_dir,
                per_device_train_batch_size=self.trainer_config.per_device_train_batch_size,
                gradient_accumulation_steps=self.trainer_config.gradient_accumulation_steps,
                warmup_steps=self.trainer_config.warmup_steps,
                max_steps=self.trainer_config.max_steps,
                learning_rate=self.trainer_config.learning_rate,
                weight_decay=self.trainer_config.weight_decay,
                lr_scheduler_type=self.trainer_config.lr_scheduler_type,
                optim=self.trainer_config.optim,
                logging_steps=self.trainer_config.logging_steps,
                save_steps=self.trainer_config.save_steps,
                eval_steps=self.trainer_config.eval_steps,
                fp16=self.trainer_config.fp16,
                bf16=self.trainer_config.bf16,
                gradient_checkpointing=self.trainer_config.gradient_checkpointing,
                dataloader_num_workers=self.trainer_config.dataloader_num_workers,
                remove_unused_columns=self.trainer_config.remove_unused_columns,
                report_to="none",
                save_total_limit=3,
                beta=self.dpo_config.beta,
                loss_type=self.dpo_config.loss_type,
                max_prompt_length=self.dpo_config.max_prompt_length,
                max_length=self.dpo_config.max_length,
                reference_free=self.dpo_config.reference_free,
            )
            
            trainer = DPOTrainer(
                model=self._model,
                ref_model=self._ref_model,
                tokenizer=self._tokenizer,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                args=dpo_args,
            )
            
            if progress_callback:
                trainer.add_callback(ProgressCallback(progress_callback, run_id))
            
            loop = asyncio.get_event_loop()
            train_result = await loop.run_in_executor(None, trainer.train)
            
            adapter_path = f"{output_dir}/adapter"
            trainer.model.save_pretrained(adapter_path)
            self._tokenizer.save_pretrained(adapter_path)
            
            duration = int(time.time() - start_time)
            
            metrics = {
                "train_loss": train_result.training_loss,
                "train_steps": train_result.global_step,
                "epoch": train_result.epoch,
            }
            
            if eval_dataset:
                eval_result = await loop.run_in_executor(None, trainer.evaluate)
                metrics["eval_loss"] = eval_result.get("eval_loss")
            
            logger.info("dpo_training_completed", run_id=run_id, duration=duration, metrics=metrics)
            
            return TrainingResult(
                success=True,
                output_dir=output_dir,
                adapter_path=adapter_path,
                metrics=metrics,
                duration_seconds=duration,
            )
            
        except Exception as e:
            logger.error("dpo_training_failed", run_id=run_id, error=str(e))
            return TrainingResult(
                success=False,
                output_dir=output_dir,
                adapter_path="",
                metrics={},
                duration_seconds=int(time.time() - start_time),
                error=str(e),
            )
        finally:
            await self._cleanup()
    
    async def _load_model(self, load_ref: bool = False):
        """Load model with Unsloth optimization."""
        from unsloth import FastLanguageModel
        
        loop = asyncio.get_event_loop()
        
        def load():
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.base_model,
                max_seq_length=self.unsloth_config.max_seq_length,
                dtype=None,
                load_in_4bit=self.unsloth_config.load_in_4bit,
            )
            
            model = FastLanguageModel.get_peft_model(
                model,
                r=self.lora_config.r,
                target_modules=self.lora_config.target_modules,
                lora_alpha=self.lora_config.alpha,
                lora_dropout=self.lora_config.dropout,
                bias=self.lora_config.bias,
                use_gradient_checkpointing=self.unsloth_config.use_gradient_checkpointing,
                random_state=self.unsloth_config.random_state,
            )
            
            return model, tokenizer
        
        self._model, self._tokenizer = await loop.run_in_executor(None, load)
        
        if load_ref:
            def load_ref_model():
                ref_model, _ = FastLanguageModel.from_pretrained(
                    model_name=self.config.base_model,
                    max_seq_length=self.unsloth_config.max_seq_length,
                    dtype=None,
                    load_in_4bit=self.unsloth_config.load_in_4bit,
                )
                return ref_model
            
            self._ref_model = await loop.run_in_executor(None, load_ref_model)
        
        logger.info("model_loaded_for_training", base_model=self.config.base_model)
    
    async def _cleanup(self):
        """Clean up model references to free GPU memory."""
        if self._model:
            del self._model
            self._model = None
        if self._ref_model:
            del self._ref_model
            self._ref_model = None
        if self._tokenizer:
            del self._tokenizer
            self._tokenizer = None
        torch.cuda.empty_cache()


class ProgressCallback:
    """Callback for training progress updates."""
    
    def __init__(self, callback: callable, run_id: str):
        self.callback = callback
        self.run_id = run_id
    
    def on_log(self, args, state, control, **kwargs):
        if state.log_history:
            latest = state.log_history[-1]
            progress = state.global_step / state.max_steps if state.max_steps > 0 else 0
            asyncio.create_task(self.callback({
                "run_id": self.run_id,
                "step": state.global_step,
                "max_steps": state.max_steps,
                "progress": progress,
                "epoch": state.epoch,
                "loss": latest.get("loss"),
                "learning_rate": latest.get("learning_rate"),
                "grad_norm": latest.get("grad_norm"),
            }))


# Singleton
_trainer: Optional[LoRATrainer] = None
_trainer_lock = asyncio.Lock()


async def get_trainer() -> LoRATrainer:
    global _trainer
    async with _trainer_lock:
        if _trainer is None:
            _trainer = LoRATrainer()
        return _trainer