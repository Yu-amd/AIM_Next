"""
Model Sizing Utilities for GPU Memory Partitioning

This module provides utilities to determine memory requirements for models
and validate model compatibility with GPU partitions.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelSizeInfo:
    """Information about a model's memory requirements."""
    model_id: str
    parameters: str
    memory_gb: float  # Base memory (FP16) for backward compatibility
    quantization: List[str]
    recommended_partition_gb: float
    precision_memory: Optional[Dict[str, float]] = None  # Precision-specific memory: {"fp16": 20.0, "int8": 13.0, "int4": 9.0}


@dataclass
class GPUSpec:
    """GPU specification information."""
    total_memory_gb: int
    compute_units: int
    recommended_partitions: List[int]


class ModelSizingConfig:
    """Manages model sizing configuration for memory partitioning."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize model sizing configuration.
        
        Args:
            config_path: Path to model sizing config YAML file.
                        Defaults to model_sizing_config.yaml in same directory.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "model_sizing_config.yaml"
        
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Model sizing config not found: {self.config_path}"
            )
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.models = {}
        for model_id, info in self.config.get('models', {}).items():
            # Handle precision_memory if present
            precision_memory = info.get('precision_memory')
            if precision_memory:
                # Ensure all required fields are present
                if 'memory_gb' not in info:
                    info['memory_gb'] = precision_memory.get('fp16', 0)
            self.models[model_id] = ModelSizeInfo(**info)
        
        self.gpu_specs = {
            gpu_name: GPUSpec(**spec)
            for gpu_name, spec in self.config.get('gpu_specs', {}).items()
        }
        
        self.partition_config = self.config.get('partition_config', {})
    
    def get_model_size(self, model_id: str) -> Optional[ModelSizeInfo]:
        """
        Get memory size information for a model.
        
        Args:
            model_id: Model identifier (e.g., "meta-llama/Llama-3.1-8B-Instruct")
        
        Returns:
            ModelSizeInfo if found, None otherwise
        """
        # Try exact match first
        if model_id in self.models:
            return self.models[model_id]
        
        # Try partial match (e.g., model name without org)
        for key, info in self.models.items():
            if model_id.endswith(key.split('/')[-1]):
                return info
        
        return None
    
    def estimate_model_size(
        self,
        model_id: str,
        parameters: Optional[str] = None,
        precision: str = "fp16"
    ) -> float:
        """
        Estimate memory requirement for a model.
        
        Args:
            model_id: Model identifier
            parameters: Model parameter count (e.g., "7B", "13B")
            precision: Precision level ("fp16", "int8", "int4")
        
        Returns:
            Estimated memory requirement in GB
        """
        # Try to get from config
        model_info = self.get_model_size(model_id)
        if model_info:
            # Check for precision-specific memory
            if model_info.precision_memory and precision in model_info.precision_memory:
                return model_info.precision_memory[precision]
            # Fallback to base memory (FP16)
            return model_info.memory_gb
        
        # Fallback: Estimate based on parameters
        if parameters:
            try:
                param_count = self._parse_parameters(parameters)
                # Rough estimate based on precision
                bytes_per_param = {
                    "fp16": 2,
                    "int8": 1,
                    "int4": 0.5
                }.get(precision, 2)
                # Add 20% overhead for KV cache, activations, etc.
                memory_gb = (param_count * bytes_per_param * 1.2) / (1024 ** 3)
                return memory_gb
            except ValueError:
                pass
        
        # Default fallback: assume 40GB for unknown models (FP16)
        return 40.0
    
    def _parse_parameters(self, param_str: str) -> int:
        """Parse parameter string to integer count."""
        param_str = param_str.upper().strip()
        
        multipliers = {
            'B': 1_000_000_000,
            'M': 1_000_000,
            'K': 1_000,
        }
        
        for suffix, multiplier in multipliers.items():
            if param_str.endswith(suffix):
                num = float(param_str[:-1])
                return int(num * multiplier)
        
        return int(float(param_str))
    
    def get_gpu_spec(self, gpu_name: str) -> Optional[GPUSpec]:
        """
        Get GPU specification.
        
        Args:
            gpu_name: GPU model name (e.g., "MI300X")
        
        Returns:
            GPUSpec if found, None otherwise
        """
        return self.gpu_specs.get(gpu_name.upper())
    
    def validate_model_fits_partition(
        self,
        model_id: str,
        partition_size_gb: float,
        gpu_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that a model fits in a partition.
        
        Args:
            model_id: Model identifier
            partition_size_gb: Available partition size in GB
            gpu_name: Optional GPU name for additional validation
        
        Returns:
            Tuple of (fits, error_message)
        """
        model_size = self.estimate_model_size(model_id)
        
        # Get system overhead
        overhead = self.partition_config.get('system_overhead_gb', 4)
        available = partition_size_gb - overhead
        
        if model_size > available:
            return False, (
                f"Model {model_id} requires {model_size:.1f}GB but partition "
                f"only has {available:.1f}GB available "
                f"(partition: {partition_size_gb}GB, overhead: {overhead}GB)"
            )
        
        # Check minimum partition size
        min_partition = self.partition_config.get('min_partition_gb', 8)
        if partition_size_gb < min_partition:
            return False, (
                f"Partition size {partition_size_gb}GB is below minimum "
                f"{min_partition}GB"
            )
        
        return True, None
    
    def calculate_optimal_partitions(
        self,
        gpu_name: str,
        model_ids: List[str]
    ) -> List[Dict[str, any]]:
        """
        Calculate optimal partition allocation for models on a GPU.
        
        Args:
            gpu_name: GPU model name
            model_ids: List of model identifiers to deploy
        
        Returns:
            List of partition configurations
        """
        gpu_spec = self.get_gpu_spec(gpu_name)
        if not gpu_spec:
            raise ValueError(f"Unknown GPU: {gpu_name}")
        
        # Get model sizes
        model_sizes = []
        for model_id in model_ids:
            size = self.estimate_model_size(model_id)
            model_sizes.append({
                'model_id': model_id,
                'size_gb': size,
            })
        
        # Sort by size (largest first)
        model_sizes.sort(key=lambda x: x['size_gb'], reverse=True)
        
        total_memory = gpu_spec.total_memory_gb
        overhead = self.partition_config.get('system_overhead_gb', 4)
        available = total_memory - overhead
        
        # Calculate partitions
        partitions = []
        current_partition = {
            'partition_id': 0,
            'models': [],
            'total_size_gb': 0,
            'allocated_gb': 0,
        }
        
        min_partition = self.partition_config.get('min_partition_gb', 8)
        max_partitions = self.partition_config.get('max_partitions', 8)
        
        for model in model_sizes:
            model_size = model['size_gb']
            needed = model_size + overhead  # Add overhead per model
            
            # Check if model fits in current partition
            if (current_partition['total_size_gb'] + needed <= 
                available / max_partitions):
                current_partition['models'].append(model['model_id'])
                current_partition['total_size_gb'] += needed
                current_partition['allocated_gb'] = max(
                    current_partition['allocated_gb'],
                    current_partition['total_size_gb']
                )
            else:
                # Start new partition
                if current_partition['models']:
                    partitions.append(current_partition)
                
                if len(partitions) >= max_partitions:
                    raise ValueError(
                        f"Cannot fit all models: maximum {max_partitions} "
                        f"partitions reached"
                    )
                
                current_partition = {
                    'partition_id': len(partitions),
                    'models': [model['model_id']],
                    'total_size_gb': needed,
                    'allocated_gb': needed,
                }
        
        # Add last partition
        if current_partition['models']:
            partitions.append(current_partition)
        
        # Validate all models fit
        total_allocated = sum(p['allocated_gb'] for p in partitions)
        if total_allocated > available:
            raise ValueError(
                f"Total memory required {total_allocated:.1f}GB exceeds "
                f"available {available:.1f}GB on {gpu_name}"
            )
        
        return partitions

