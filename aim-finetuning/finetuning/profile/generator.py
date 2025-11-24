"""
AIM profile generator for fine-tuned models.

Generates AIM-compatible profiles for fine-tuned models, including
resource requirements and deployment configuration.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AIMProfile:
    """AIM profile structure for fine-tuned models."""
    model_id: str
    base_model_id: str
    fine_tuning_method: str  # "lora", "qlora", "full"
    precision: str  # "fp16", "bf16", "fp8"
    memory_gb: float
    recommended_partition_gb: float
    parameters: str  # e.g., "7B"
    quantization_info: Optional[Dict[str, Any]] = None
    lora_config: Optional[Dict[str, Any]] = None
    training_info: Optional[Dict[str, Any]] = None


class AIMProfileGenerator:
    """Generate AIM profiles for fine-tuned models."""
    
    def __init__(self, base_model_profile: Optional[Dict[str, Any]] = None):
        """
        Initialize profile generator.
        
        Args:
            base_model_profile: Optional base model AIM profile to reference
        """
        self.base_model_profile = base_model_profile
    
    def estimate_model_size(
        self,
        base_model_id: str,
        method: str,
        precision: str = "fp16"
    ) -> float:
        """
        Estimate model size in GB based on method and precision.
        
        Args:
            base_model_id: Base model identifier
            method: Fine-tuning method ("lora", "qlora", "full")
            precision: Model precision ("fp16", "bf16", "fp8")
            
        Returns:
            Estimated model size in GB
        """
        # Extract parameter count from model ID (e.g., "7B", "13B")
        import re
        param_match = re.search(r'(\d+(?:\.\d+)?)B', base_model_id)
        if param_match:
            params = float(param_match.group(1))
        else:
            # Default estimates
            params = 7.0  # Default to 7B
        
        # Base memory estimates (GB) per billion parameters
        precision_multipliers = {
            "fp16": 2.0,  # 2 bytes per parameter
            "bf16": 2.0,  # 2 bytes per parameter
            "fp8": 1.0,   # 1 byte per parameter
            "int8": 1.0,  # 1 byte per parameter
            "int4": 0.5,  # 0.5 bytes per parameter
        }
        
        multiplier = precision_multipliers.get(precision, 2.0)
        base_memory = params * multiplier
        
        # Adjust based on fine-tuning method
        if method == "lora":
            # LoRA adds minimal overhead (~1-5% of base model)
            memory = base_memory * 1.05
        elif method == "qlora":
            # QLoRA uses 4-bit base + LoRA adapters
            # 4-bit quantization: ~0.5 bytes per parameter
            quantized_base = params * 0.5
            lora_overhead = base_memory * 0.05
            memory = quantized_base + lora_overhead
        elif method == "full":
            # Full fine-tuning uses same memory as base
            memory = base_memory
        else:
            memory = base_memory
        
        # Add overhead for inference (activations, KV cache, etc.)
        # Typically 1.25-1.5x for inference
        inference_overhead = 1.3
        memory = memory * inference_overhead
        
        return round(memory, 2)
    
    def generate_profile(
        self,
        model_id: str,
        base_model_id: str,
        method: str,
        precision: str = "fp16",
        training_info: Optional[Dict[str, Any]] = None,
        lora_config: Optional[Dict[str, Any]] = None,
        quantization_info: Optional[Dict[str, Any]] = None
    ) -> AIMProfile:
        """
        Generate AIM profile for fine-tuned model.
        
        Args:
            model_id: Fine-tuned model identifier
            base_model_id: Base model identifier
            method: Fine-tuning method ("lora", "qlora", "full")
            precision: Model precision
            training_info: Optional training metadata
            lora_config: Optional LoRA configuration
            quantization_info: Optional quantization configuration
            
        Returns:
            AIMProfile object
        """
        # Estimate memory requirements
        memory_gb = self.estimate_model_size(base_model_id, method, precision)
        
        # Recommended partition size (add 25% buffer)
        recommended_partition_gb = memory_gb * 1.25
        
        # Extract parameter count
        import re
        param_match = re.search(r'(\d+(?:\.\d+)?)B', base_model_id)
        parameters = param_match.group(1) + "B" if param_match else "unknown"
        
        profile = AIMProfile(
            model_id=model_id,
            base_model_id=base_model_id,
            fine_tuning_method=method,
            precision=precision,
            memory_gb=memory_gb,
            recommended_partition_gb=round(recommended_partition_gb, 2),
            parameters=parameters,
            quantization_info=quantization_info,
            lora_config=lora_config,
            training_info=training_info
        )
        
        logger.info(f"Generated AIM profile for {model_id}")
        logger.info(f"  Method: {method}, Precision: {precision}")
        logger.info(f"  Memory: {memory_gb} GB, Recommended partition: {recommended_partition_gb:.2f} GB")
        
        return profile
    
    def save_profile(
        self,
        profile: AIMProfile,
        output_path: str
    ) -> str:
        """
        Save AIM profile to JSON file.
        
        Args:
            profile: AIMProfile object
            output_path: Path to save profile
            
        Returns:
            Path to saved profile file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        profile_dict = asdict(profile)
        
        # Remove None values
        profile_dict = {k: v for k, v in profile_dict.items() if v is not None}
        
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(profile_dict, f, indent=2)
        
        logger.info(f"AIM profile saved to {output_path}")
        return str(output_path)
    
    def load_profile(self, profile_path: str) -> AIMProfile:
        """
        Load AIM profile from JSON file.
        
        Args:
            profile_path: Path to profile file
            
        Returns:
            AIMProfile object
        """
        with open(profile_path, 'r') as f:
            profile_dict = json.load(f)
        
        return AIMProfile(**profile_dict)

