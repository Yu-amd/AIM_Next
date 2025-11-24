"""
Base trainer class for AIM fine-tuning microservice.

Provides common functionality for all fine-tuning methods (LoRA, QLoRA, Full).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for fine-tuning training."""
    model_id: str
    output_dir: str
    learning_rate: float = 2e-4
    batch_size: int = 4
    epochs: int = 3
    gradient_accumulation_steps: int = 1
    max_seq_length: int = 2048
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: Optional[int] = None
    save_total_limit: int = 3
    fp16: bool = True
    bf16: bool = False
    gradient_checkpointing: bool = True
    dataloader_num_workers: int = 4
    seed: int = 42


@dataclass
class ModelConfig:
    """Model configuration."""
    model_id: str
    trust_remote_code: bool = False
    use_flash_attention: bool = True
    torch_dtype: str = "float16"


class BaseTrainer(ABC):
    """Base class for all fine-tuning trainers."""
    
    def __init__(
        self,
        training_config: TrainingConfig,
        model_config: ModelConfig,
        dataset_path: str,
        output_dir: str
    ):
        """
        Initialize base trainer.
        
        Args:
            training_config: Training configuration
            model_config: Model configuration
            dataset_path: Path to training dataset
            output_dir: Output directory for checkpoints and final model
        """
        self.training_config = training_config
        self.model_config = model_config
        self.dataset_path = dataset_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.tokenizer = None
        self.trainer = None
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the base model and tokenizer."""
        pass
    
    @abstractmethod
    def prepare_model_for_training(self) -> None:
        """Prepare model for training (apply LoRA, quantization, etc.)."""
        pass
    
    @abstractmethod
    def create_trainer(self, train_dataset, eval_dataset=None) -> None:
        """Create the HuggingFace Trainer instance."""
        pass
    
    @abstractmethod
    def train(self) -> Dict[str, Any]:
        """
        Execute training.
        
        Returns:
            Dictionary with training metrics and results
        """
        pass
    
    def save_model(self, checkpoint_dir: Optional[str] = None) -> str:
        """
        Save the fine-tuned model.
        
        Args:
            checkpoint_dir: Optional checkpoint directory. If None, saves to output_dir.
            
        Returns:
            Path to saved model
        """
        save_path = Path(checkpoint_dir) if checkpoint_dir else self.output_dir
        save_path.mkdir(parents=True, exist_ok=True)
        
        if self.model and self.tokenizer:
            self.model.save_pretrained(str(save_path))
            self.tokenizer.save_pretrained(str(save_path))
            logger.info(f"Model saved to {save_path}")
        
        return str(save_path)
    
    def get_training_info(self) -> Dict[str, Any]:
        """
        Get information about the training setup.
        
        Returns:
            Dictionary with training information
        """
        return {
            "model_id": self.model_config.model_id,
            "output_dir": str(self.output_dir),
            "training_config": {
                "learning_rate": self.training_config.learning_rate,
                "batch_size": self.training_config.batch_size,
                "epochs": self.training_config.epochs,
                "max_seq_length": self.training_config.max_seq_length,
            },
            "method": self.__class__.__name__,
        }

