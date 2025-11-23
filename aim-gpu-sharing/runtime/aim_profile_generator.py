"""
AIM Profile Generator for Models with Multiple Precision Levels

This module generates AIM profiles for models with different quantization
levels (FP16, INT8, INT4) and their corresponding memory requirements.
"""

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Handle both relative and absolute imports
try:
    from .model_sizing import ModelSizingConfig
except ImportError:
    from model_sizing import ModelSizingConfig


@dataclass
class PrecisionVariant:
    """Memory requirements for a specific precision level."""
    precision: str  # "fp16", "int8", "int4"
    memory_gb: float
    recommended_partition_gb: float


@dataclass
class AIMProfile:
    """AIM profile structure for a model variant."""
    model_id: str
    variant_id: str  # e.g., "meta-llama/Llama-3.1-8B-Instruct-fp16"
    version: str
    parameters: str
    precision: str
    memory_requirement_gb: float
    recommended_partition_gb: float
    gpu_sharing: Dict
    resource_requirements: Dict
    metadata: Dict


class AIMProfileGenerator:
    """Generates AIM profiles for models with multiple precision levels."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize profile generator.
        
        Args:
            config_path: Path to model sizing config YAML file
        """
        self.sizing_config = ModelSizingConfig(config_path)
        self.profiles: Dict[str, AIMProfile] = {}
    
    def generate_profiles_for_model(
        self,
        model_id: str,
        precision_variants: List[PrecisionVariant],
        base_version: str = "1.0.0"
    ) -> List[AIMProfile]:
        """
        Generate AIM profiles for a model with multiple precision variants.
        
        Args:
            model_id: Model identifier
            precision_variants: List of precision variants with memory requirements
            base_version: Base version string
        
        Returns:
            List of AIM profiles (one per precision variant)
        """
        model_info = self.sizing_config.get_model_size(model_id)
        if not model_info:
            # Try to estimate
            parameters = "unknown"
        else:
            parameters = model_info.parameters
        
        profiles = []
        
        for variant in precision_variants:
            variant_id = f"{model_id}-{variant.precision}"
            version = f"{base_version}-{variant.precision}"
            
            profile = AIMProfile(
                model_id=model_id,
                variant_id=variant_id,
                version=version,
                parameters=parameters,
                precision=variant.precision,
                memory_requirement_gb=variant.memory_gb,
                recommended_partition_gb=variant.recommended_partition_gb,
                gpu_sharing={
                    "enabled": True,
                    "memory_limit_gb": variant.recommended_partition_gb,
                    "partition_id": None,  # Will be assigned by scheduler
                    "qos_priority": "medium"
                },
                resource_requirements={
                    "gpu_memory_gb": variant.memory_gb,
                    "gpu_count": 1,
                    "cpu_cores": 2,
                    "system_memory_gb": 16
                },
                metadata={
                    "quantization": variant.precision,
                    "base_model": model_id,
                    "parameters": parameters
                }
            )
            
            profiles.append(profile)
            self.profiles[variant_id] = profile
        
        return profiles
    
    def generate_all_profiles(self) -> Dict[str, List[AIMProfile]]:
        """
        Generate AIM profiles for all models in the configuration.
        
        Returns:
            Dictionary mapping model_id to list of profiles
        """
        all_profiles = {}
        
        for model_id, model_info in self.sizing_config.models.items():
            # Extract precision variants from model info
            variants = []
            
            # Check if model has precision-specific memory requirements
            if model_info.precision_memory:
                # Model has explicit precision memory requirements
                for precision, memory_gb in model_info.precision_memory.items():
                    variants.append(PrecisionVariant(
                        precision=precision,
                        memory_gb=memory_gb,
                        recommended_partition_gb=memory_gb * 1.25
                    ))
            else:
                # Fallback: Use base memory and estimate for other precisions
                base_memory = model_info.memory_gb
                
                # FP16 (baseline)
                variants.append(PrecisionVariant(
                    precision="fp16",
                    memory_gb=base_memory,
                    recommended_partition_gb=model_info.recommended_partition_gb
                ))
                
                # INT8 (approximately 60% of FP16)
                variants.append(PrecisionVariant(
                    precision="int8",
                    memory_gb=base_memory * 0.6,
                    recommended_partition_gb=base_memory * 0.6 * 1.25
                ))
                
                # INT4 (approximately 40% of FP16)
                variants.append(PrecisionVariant(
                    precision="int4",
                    memory_gb=base_memory * 0.4,
                    recommended_partition_gb=base_memory * 0.4 * 1.25
                ))
            
            profiles = self.generate_profiles_for_model(model_id, variants)
            all_profiles[model_id] = profiles
        
        return all_profiles
    
    def save_profile(self, profile: AIMProfile, output_dir: Path):
        """
        Save an AIM profile to a JSON file.
        
        Args:
            profile: AIM profile to save
            output_dir: Directory to save profile
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from variant_id
        safe_name = profile.variant_id.replace("/", "_").replace(":", "_")
        profile_path = output_dir / f"{safe_name}.json"
        
        profile_dict = asdict(profile)
        
        with open(profile_path, 'w') as f:
            json.dump(profile_dict, f, indent=2)
        
        return profile_path
    
    def save_all_profiles(self, output_dir: Path):
        """
        Save all generated profiles to files.
        
        Args:
            output_dir: Directory to save profiles
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for variant_id, profile in self.profiles.items():
            path = self.save_profile(profile, output_dir)
            saved_paths.append(path)
        
        return saved_paths
    
    def get_profile(self, variant_id: str) -> Optional[AIMProfile]:
        """Get a profile by variant ID."""
        return self.profiles.get(variant_id)
    
    def list_profiles(self) -> List[str]:
        """List all generated profile variant IDs."""
        return list(self.profiles.keys())

