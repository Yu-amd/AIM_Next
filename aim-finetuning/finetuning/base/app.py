"""
Main application entry point for fine-tuning service.

Handles CLI arguments, configuration, and training orchestration.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from finetuning.methods.lora_trainer import LoRATrainer
from finetuning.methods.qlora_trainer import QLoRATrainer
from finetuning.methods.full_trainer import FullTrainer
from finetuning.base.trainer_base import TrainingConfig, ModelConfig
from finetuning.profile.generator import AIMProfileGenerator

# Optional monitoring imports
try:
    from monitoring.metrics import FineTuningMetricsExporter, TrainingMetrics, get_gpu_metrics
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def create_training_config(args: argparse.Namespace, config: Dict[str, Any]) -> TrainingConfig:
    """Create TrainingConfig from args and config."""
    return TrainingConfig(
        model_id=config.get("model_id", args.model_id),
        output_dir=config.get("output_dir", args.output_dir),
        learning_rate=config.get("hyperparameters", {}).get("learning_rate", args.learning_rate),
        batch_size=config.get("hyperparameters", {}).get("batch_size", args.batch_size),
        epochs=config.get("hyperparameters", {}).get("epochs", args.epochs),
        gradient_accumulation_steps=config.get("hyperparameters", {}).get("gradient_accumulation_steps", 1),
        max_seq_length=config.get("hyperparameters", {}).get("max_seq_length", 2048),
        warmup_steps=config.get("hyperparameters", {}).get("warmup_steps", 100),
        logging_steps=config.get("hyperparameters", {}).get("logging_steps", 10),
        save_steps=config.get("hyperparameters", {}).get("save_steps", 500),
        eval_steps=config.get("hyperparameters", {}).get("eval_steps"),
        save_total_limit=config.get("hyperparameters", {}).get("save_total_limit", 3),
        fp16=config.get("hyperparameters", {}).get("fp16", True),
        bf16=config.get("hyperparameters", {}).get("bf16", False),
        gradient_checkpointing=config.get("hyperparameters", {}).get("gradient_checkpointing", True),
        seed=config.get("hyperparameters", {}).get("seed", 42),
    )


def create_model_config(args: argparse.Namespace, config: Dict[str, Any]) -> ModelConfig:
    """Create ModelConfig from args and config."""
    return ModelConfig(
        model_id=config.get("model_id", args.model_id),
        trust_remote_code=config.get("trust_remote_code", False),
        use_flash_attention=config.get("use_flash_attention", True),
        torch_dtype=config.get("torch_dtype", "float16"),
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AIM Fine-Tuning Service")
    
    # Model and dataset
    parser.add_argument("--model-id", type=str, required=True, help="HuggingFace model ID")
    parser.add_argument("--dataset-path", type=str, required=True, help="Path to training dataset")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory for model")
    
    # Method
    parser.add_argument("--method", type=str, default="lora", choices=["lora", "qlora", "full"],
                       help="Fine-tuning method")
    
    # Training hyperparameters
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--max-seq-length", type=int, default=2048, help="Maximum sequence length")
    
    # Monitoring
    parser.add_argument("--enable-metrics", action="store_true", help="Enable Prometheus metrics export")
    parser.add_argument("--metrics-port", type=int, default=8000, help="Metrics server port")
    
    # LoRA specific
    parser.add_argument("--lora-rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    
    # Config file
    parser.add_argument("--config", type=str, help="Path to JSON configuration file")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Create configs
    training_config = create_training_config(args, config)
    model_config = create_model_config(args, config)
    
    logger.info("Starting fine-tuning...")
    logger.info(f"Model: {model_config.model_id}")
    logger.info(f"Method: {args.method}")
    logger.info(f"Dataset: {args.dataset_path}")
    logger.info(f"Output: {args.output_dir}")
    
    # Initialize metrics exporter if enabled
    metrics_exporter = None
    if args.enable_metrics and MONITORING_AVAILABLE:
        try:
            metrics_exporter = FineTuningMetricsExporter(port=args.metrics_port)
            metrics_exporter.start_server()
            logger.info(f"Metrics exporter started on port {args.metrics_port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics exporter: {e}")
            metrics_exporter = None
    elif args.enable_metrics and not MONITORING_AVAILABLE:
        logger.warning("Metrics export requested but prometheus_client not installed")
    
    # Create trainer based on method
    if args.method == "lora":
        lora_config = config.get("lora_config", {
            "r": args.lora_rank,
            "lora_alpha": args.lora_alpha,
            "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": "CAUSAL_LM"
        })
        
        trainer = LoRATrainer(
            training_config=training_config,
            model_config=model_config,
            dataset_path=args.dataset_path,
            output_dir=args.output_dir,
            lora_config=lora_config
        )
    elif args.method == "qlora":
        lora_config = config.get("lora_config", {
            "r": args.lora_rank,
            "lora_alpha": args.lora_alpha,
            "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": "CAUSAL_LM"
        })
        
        quantization_config = config.get("quantization_config", {
            "load_in_4bit": True,
            "bnb_4bit_compute_dtype": "float16",
            "bnb_4bit_use_double_quant": True,
            "bnb_4bit_quant_type": "nf4"
        })
        
        trainer = QLoRATrainer(
            training_config=training_config,
            model_config=model_config,
            dataset_path=args.dataset_path,
            output_dir=args.output_dir,
            lora_config=lora_config,
            quantization_config=quantization_config
        )
    elif args.method == "full":
        trainer = FullTrainer(
            training_config=training_config,
            model_config=model_config,
            dataset_path=args.dataset_path,
            output_dir=args.output_dir
        )
    else:
        raise ValueError(f"Unknown method: {args.method}")
    
    # Train
    try:
        # Update metrics if enabled
        if metrics_exporter:
            job_name = Path(args.output_dir).name
            metrics_exporter.update_job_status(
                job_name=job_name,
                model_id=model_config.model_id,
                method=args.method,
                status="Running"
            )
        
        results = trainer.train()
        logger.info("Training completed successfully")
        logger.info(f"Results: {results}")
        
        # Update metrics with final results
        if metrics_exporter:
            job_name = Path(args.output_dir).name
            gpu_metrics = get_gpu_metrics()
            
            training_metrics = TrainingMetrics(
                job_name=job_name,
                model_id=model_config.model_id,
                method=args.method,
                current_epoch=training_config.epochs,
                total_epochs=training_config.epochs,
                current_step=0,  # Would need to track during training
                total_steps=0,
                train_loss=results.get("train_loss", 0.0),
                learning_rate=training_config.learning_rate,
                gpu_utilization=gpu_metrics.get("gpu_utilization"),
                gpu_memory_used=gpu_metrics.get("gpu_memory_used"),
                gpu_memory_total=gpu_metrics.get("gpu_memory_total"),
                samples_per_second=results.get("train_samples_per_second"),
                tokens_per_second=None
            )
            
            metrics_exporter.update_training_metrics(training_metrics)
            metrics_exporter.update_job_status(
                job_name=job_name,
                model_id=model_config.model_id,
                method=args.method,
                status="Succeeded"
            )
        
        # Save training info
        training_info = trainer.get_training_info()
        training_info["results"] = results
        
        info_path = Path(args.output_dir) / "training_info.json"
        with open(info_path, 'w') as f:
            json.dump(training_info, f, indent=2)
        
        logger.info(f"Training info saved to {info_path}")
        
        # Generate AIM profile
        try:
            logger.info("Generating AIM profile...")
            profile_generator = AIMProfileGenerator()
            
            # Get LoRA config if available
            lora_config = None
            quantization_info = None
            if hasattr(trainer, 'lora_config'):
                lora_config = trainer.lora_config
            if hasattr(trainer, 'quantization_config'):
                quantization_info = trainer.quantization_config
            
            # Determine precision from model config
            precision = model_config.torch_dtype.replace("float", "fp").replace("bfloat", "bf")
            if precision == "fp32":
                precision = "fp16"  # Default to fp16 for inference
            
            profile = profile_generator.generate_profile(
                model_id=f"{model_config.model_id}-finetuned",
                base_model_id=model_config.model_id,
                method=args.method,
                precision=precision,
                training_info=training_info,
                lora_config=lora_config,
                quantization_info=quantization_info
            )
            
            # Save profile
            profile_path = Path(args.output_dir) / "aim_profile.json"
            profile_generator.save_profile(profile, str(profile_path))
            logger.info(f"AIM profile saved to {profile_path}")
            
        except Exception as e:
            logger.warning(f"Failed to generate AIM profile: {e}")
            logger.warning("Training completed successfully, but profile generation failed")
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

