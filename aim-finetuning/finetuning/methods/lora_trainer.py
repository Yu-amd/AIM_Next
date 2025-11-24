"""
LoRA (Low-Rank Adaptation) trainer implementation.

Parameter-efficient fine-tuning using LoRA adapters.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
import logging

from finetuning.base.trainer_base import BaseTrainer, TrainingConfig, ModelConfig
from finetuning.dataset.loader import DatasetLoader
from finetuning.dataset.preprocessor import DatasetPreprocessor

logger = logging.getLogger(__name__)


class LoRATrainer(BaseTrainer):
    """LoRA fine-tuning trainer."""
    
    def __init__(
        self,
        training_config: TrainingConfig,
        model_config: ModelConfig,
        dataset_path: str,
        output_dir: str,
        lora_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize LoRA trainer.
        
        Args:
            training_config: Training configuration
            model_config: Model configuration
            dataset_path: Path to training dataset
            output_dir: Output directory
            lora_config: LoRA configuration (rank, alpha, target_modules, etc.)
        """
        super().__init__(training_config, model_config, dataset_path, output_dir)
        
        # Default LoRA config
        self.lora_config = lora_config or {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": "CAUSAL_LM"
        }
    
    def load_model(self) -> None:
        """Load base model and tokenizer."""
        logger.info(f"Loading model: {self.model_config.model_id}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_config.model_id,
            trust_remote_code=self.model_config.trust_remote_code
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model
        torch_dtype = getattr(torch, self.model_config.torch_dtype, torch.float16)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_config.model_id,
            torch_dtype=torch_dtype,
            trust_remote_code=self.model_config.trust_remote_code,
            device_map="auto"
        )
        
        logger.info("Model and tokenizer loaded successfully")
    
    def prepare_model_for_training(self) -> None:
        """Apply LoRA adapters to model."""
        if self.model is None:
            self.load_model()
        
        logger.info("Applying LoRA adapters...")
        logger.info(f"LoRA config: {self.lora_config}")
        
        peft_config = LoraConfig(
            r=self.lora_config["r"],
            lora_alpha=self.lora_config["lora_alpha"],
            target_modules=self.lora_config["target_modules"],
            lora_dropout=self.lora_config["lora_dropout"],
            bias=self.lora_config["bias"],
            task_type=TaskType.CAUSAL_LM
        )
        
        self.model = get_peft_model(self.model, peft_config)
        self.model.print_trainable_parameters()
        
        logger.info("LoRA adapters applied")
    
    def create_trainer(
        self,
        train_dataset,
        eval_dataset=None
    ) -> None:
        """Create HuggingFace Trainer instance."""
        if self.model is None:
            self.prepare_model_for_training()
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            learning_rate=self.training_config.learning_rate,
            per_device_train_batch_size=self.training_config.batch_size,
            per_device_eval_batch_size=self.training_config.batch_size,
            gradient_accumulation_steps=self.training_config.gradient_accumulation_steps,
            num_train_epochs=self.training_config.epochs,
            max_steps=-1,
            warmup_steps=self.training_config.warmup_steps,
            logging_steps=self.training_config.logging_steps,
            save_steps=self.training_config.save_steps,
            eval_steps=self.training_config.eval_steps,
            save_total_limit=self.training_config.save_total_limit,
            fp16=self.training_config.fp16,
            bf16=self.training_config.bf16,
            gradient_checkpointing=self.training_config.gradient_checkpointing,
            dataloader_num_workers=self.training_config.dataloader_num_workers,
            seed=self.training_config.seed,
            report_to="none",  # Can be changed to "tensorboard" or "wandb"
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer
        )
        
        logger.info("Trainer created successfully")
    
    def train(self) -> Dict[str, Any]:
        """Execute training."""
        if self.trainer is None:
            # Load model and tokenizer first (needed for preprocessing)
            if self.model is None or self.tokenizer is None:
                self.load_model()
            
            # Load and prepare dataset
            loader = DatasetLoader(self.dataset_path)
            dataset = loader.load()
            
            # Determine dataset format and validate accordingly
            if "instruction" in dataset.column_names or "output" in dataset.column_names:
                # Conversation format - validate required fields
                required_fields = ["instruction", "output"]
                if "input" in dataset.column_names:
                    # Instruction-input-output format
                    loader.validate(required_fields=required_fields + ["input"])
                else:
                    # Instruction-output format
                    loader.validate(required_fields=required_fields)
            elif "text" in dataset.column_names:
                # Plain text format
                loader.validate(required_fields=["text"])
            else:
                # Try to infer - check if any text-like field exists
                text_fields = [col for col in dataset.column_names if "text" in col.lower() or "content" in col.lower()]
                if text_fields:
                    loader.validate(required_fields=[text_fields[0]])
                else:
                    raise ValueError(
                        f"Dataset format not recognized. Expected fields: "
                        f"['instruction', 'output'] for conversation format, or ['text'] for plain text. "
                        f"Available fields: {dataset.column_names}"
                    )
            
            # Preprocess
            preprocessor = DatasetPreprocessor(
                tokenizer=self.tokenizer,
                max_length=self.training_config.max_seq_length
            )
            
            if "instruction" in dataset.column_names or "output" in dataset.column_names:
                # Determine if input field exists
                input_field = "input" if "input" in dataset.column_names else None
                dataset = preprocessor.preprocess_conversation(
                    dataset,
                    instruction_field="instruction",
                    input_field=input_field,
                    output_field="output"
                )
            else:
                # Use first text-like field
                text_field = "text" if "text" in dataset.column_names else dataset.column_names[0]
                dataset = preprocessor.preprocess_text(dataset, text_field=text_field)
            
            # Split train/eval
            train_dataset, eval_dataset = preprocessor.split_train_eval(
                dataset,
                eval_ratio=0.1,
                seed=self.training_config.seed
            )
            
            # Create trainer
            self.create_trainer(train_dataset, eval_dataset)
        
        logger.info("Starting training...")
        train_result = self.trainer.train()
        
        # Save final model
        self.save_model()
        
        logger.info("Training completed")
        
        return {
            "train_loss": train_result.training_loss,
            "train_runtime": train_result.metrics.get("train_runtime", 0),
            "train_samples_per_second": train_result.metrics.get("train_samples_per_second", 0),
            "model_path": str(self.output_dir),
            "method": "lora"
        }

