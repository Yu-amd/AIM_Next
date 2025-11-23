#!/usr/bin/env python3
"""
Update model sizing configuration with precision-specific memory requirements.

This script updates the model_sizing_config.yaml file to include
precision-specific memory requirements (FP16, INT8, INT4) based on
the data from the PDF tables.
"""

import yaml
from pathlib import Path
from typing import Dict

# Precision memory data from PDF tables
PRECISION_DATA = {
    # Cohere Models
    "CohereForAI/aya-expanse-8B": {
        "fp16": 20.0,  # 18-20GB
        "int8": 13.0,  # 12-13GB
        "int4": 9.0    # 8-9GB
    },
    "CohereForAI/aya-expanse-32B": {
        "fp16": 75.0,  # 70-75GB
        "int8": 45.0,  # 40-45GB
        "int4": 30.0   # 26-30GB
    },
    
    # DeepSeek Models
    "deepseek-ai/DeepSeek-R1-0528": {
        "fp16": 20.0,  # 18-20GB
        "int8": 13.0,  # 12-13GB
        "int4": 9.0    # 8-9GB
    },
    "deepseek-ai/Distill-Llama-8B": {
        "fp16": 20.0,  # 18-20GB
        "int8": 13.0,  # 12-13GB
        "int4": 9.0    # 8-9GB
    },
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": {
        "fp16": 165.0,  # >160GB
        "int8": 90.0,   # ~90GB
        "int4": 60.0    # 55-60GB
    },
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B": {
        "fp16": 6.0,   # 6-19GB range (1.5B)
        "int8": 4.0,   # 4-12GB range
        "int4": 3.0    # 3-8GB range
    },
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B": {
        "fp16": 19.0,  # 6-19GB range (7B)
        "int8": 12.0,  # 4-12GB range
        "int4": 8.0    # 3-8GB range
    },
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B": {
        "fp16": 37.0,
        "int8": 22.0,
        "int4": 15.0
    },
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B": {
        "fp16": 84.0,
        "int8": 49.0,
        "int4": 32.0
    },
    "deepseek-ai/DeepSeek-R1-Zero": {
        "fp16": 165.0,  # >160GB
        "int8": 90.0,   # ~90GB
        "int4": 60.0    # 55-60GB
    },
    "deepseek-ai/DeepSeek-V3": {
        "fp16": 105.0,
        "int8": 60.0,
        "int4": 35.0
    },
    "deepseek-ai/DeepSeek-V3-0324": {
        "fp16": 105.0,
        "int8": 60.0,
        "int4": 35.0
    },
    
    # Gemma Models
    "google/gemma-3-1B": {
        "fp16": 6.0,   # 6-28GB range (1-12B)
        "int8": 4.0,   # 4-18GB range
        "int4": 2.0    # 2-12GB range
    },
    "google/gemma-3-4B": {
        "fp16": 12.0,  # 6-28GB range
        "int8": 8.0,   # 4-18GB range
        "int4": 5.0    # 2-12GB range
    },
    "google/gemma-3-12B": {
        "fp16": 28.0,  # 6-28GB range
        "int8": 18.0,  # 4-18GB range
        "int4": 12.0   # 2-12GB range
    },
    "google/gemma-3-27B": {
        "fp16": 60.0,  # ≈60GB
        "int8": 35.0,  # ~35GB
        "int4": 25.0   # 22-25GB
    },
    
    # Llama Models
    "meta-llama/Llama-3.1-8B-Instruct": {
        "fp16": 20.0,  # 18-20GB
        "int8": 13.0,  # 12-13GB
        "int4": 9.0    # 8-9GB
    },
    "meta-llama/Llama-3.2-1B-Instruct": {
        "fp16": 5.0,   # 5-26GB range (1-11B)
        "int8": 3.0,   # 3-16GB range
        "int4": 2.0    # 2-10GB range
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "fp16": 10.0,  # 5-26GB range
        "int8": 6.0,   # 3-16GB range
        "int4": 4.0    # 2-10GB range
    },
    "meta-llama/Llama-3.2-11B-Instruct": {
        "fp16": 26.0,  # 5-26GB range
        "int8": 16.0,  # 3-16GB range
        "int4": 10.0   # 2-10GB range
    },
    "meta-llama/Llama-3.3-70B-Instruct": {
        "fp16": 165.0,  # >160GB
        "int8": 90.0,   # ~90GB
        "int4": 60.0    # 55-60GB
    },
    "meta-llama/Llama-4-Scout-17B": {
        "fp16": 52.0,  # 47-52GB
        "int8": 32.0,  # 30-32GB
        "int4": 21.0   # 20-21GB
    },
    
    # Mistral Models
    "mistralai/Mistral-Small-3.1-24B": {
        "fp16": 68.0,  # 60-68GB
        "int8": 40.0,  # 35-40GB
        "int4": 28.0   # 24-28GB
    },
    "mistralai/Mistral-Large": {
        "fp16": 165.0,  # >160GB
        "int8": 90.0,   # ~90GB
        "int4": 60.0    # 55-60GB
    },
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {
        "fp16": 90.0,  # 80-90GB (45B active, MoE)
        "int8": 50.0,  # 45-50GB
        "int4": 32.0   # 28-32GB
    },
    
    # Odia Models
    "OdiaGenAI-LLM/qwen_1.5_odia_7b": {
        "fp16": 20.0,  # 18-20GB
        "int8": 13.0,  # 12-13GB
        "int4": 9.0    # 8-9GB
    },
    
    # Qwen Models
    "Qwen/Qwen2.5-0.5B-Instruct": {
        "fp16": 3.0,   # 3-10GB range (0.5-3B)
        "int8": 2.0,   # 2-7GB range
        "int4": 1.0    # 1-4GB range
    },
    "Qwen/Qwen2.5-1.5B-Instruct": {
        "fp16": 5.0,   # 3-10GB range
        "int8": 3.0,   # 2-7GB range
        "int4": 2.0    # 1-4GB range
    },
    "Qwen/Qwen2.5-3B-Instruct": {
        "fp16": 10.0,  # 3-10GB range
        "int8": 7.0,   # 2-7GB range
        "int4": 4.0    # 1-4GB range
    },
    "Qwen/Qwen3-4B-Instruct": {
        "fp16": 10.0,  # 10-22GB range (4-8B)
        "int8": 7.0,   # 7-13GB range
        "int4": 5.0    # 5-9GB range
    },
    "Qwen/Qwen3-8B-Instruct": {
        "fp16": 22.0,  # 10-22GB range
        "int8": 13.0,  # 7-13GB range
        "int4": 9.0    # 5-9GB range
    },
    "Qwen/Qwen3-14B-Instruct": {
        "fp16": 38.0,
        "int8": 23.0,
        "int4": 15.0
    },
    "Qwen/Qwen3-30B-Instruct": {
        "fp16": 80.0,
        "int8": 46.0,
        "int4": 30.0
    },
    "Qwen/Qwen3-32B-Instruct": {
        "fp16": 85.0,
        "int8": 50.0,
        "int4": 33.0
    },
    "Qwen/Qwen3-235B-A22B": {
        "fp16": 128.0,  # 22B active, MoE
        "int8": 104.0,
        "int4": 92.0
    },
    
    # TinyLlama Models
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {
        "fp16": 6.0,   # 5-6GB
        "int8": 4.0,   # 3-4GB
        "int4": 3.0    # 2-3GB
    },
    
    # Unsloth Models
    "unsloth/Llama-3.2-11B-Vision": {
        "fp16": 31.0,
        "int8": 19.0,
        "int4": 13.0
    },
    "unsloth/Llama-3.2-30B-Vision": {
        "fp16": 80.0,
        "int8": 48.0,
        "int4": 31.0
    },
}


def update_config_with_precision(config_path: str):
    """Update config file with precision-specific memory requirements."""
    config_path = Path(config_path)
    
    # Load existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'models' not in config:
        print("Error: No 'models' section found in config")
        return
    
    updated_count = 0
    
    # Update each model with precision data
    for model_id, precision_data in PRECISION_DATA.items():
        if model_id in config['models']:
            model_config = config['models'][model_id]
            
            # Add precision_memory section
            model_config['precision_memory'] = precision_data
            
            # Update base memory_gb to FP16 (for backward compatibility)
            if 'memory_gb' not in model_config or model_config['memory_gb'] != precision_data['fp16']:
                model_config['memory_gb'] = precision_data['fp16']
            
            # Update recommended_partition_gb based on FP16
            if 'recommended_partition_gb' not in model_config:
                model_config['recommended_partition_gb'] = precision_data['fp16'] * 1.25
            
            updated_count += 1
            print(f"Updated: {model_id}")
        else:
            print(f"Warning: Model {model_id} not found in config")
    
    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\nUpdated {updated_count} models with precision-specific memory requirements")


if __name__ == '__main__':
    import sys
    
    config_path = Path(__file__).parent / 'model_sizing_config.yaml'
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    update_config_with_precision(config_path)

