#!/usr/bin/env python3
"""
Helper script to add model sizing entries to the configuration file.

Usage:
    python3 add_model_size.py --model "model-id" --params "7B" --memory 16.0
"""

import argparse
import yaml
from pathlib import Path
from typing import List


def add_model_entry(
    config_path: str,
    model_id: str,
    parameters: str,
    memory_gb: float,
    quantization: List[str] = None,
    recommended_partition_gb: float = None
):
    """
    Add a model entry to the configuration file.
    
    Args:
        config_path: Path to model_sizing_config.yaml
        model_id: Model identifier (e.g., "cohere/Command-R")
        parameters: Parameter count (e.g., "7B", "13B")
        memory_gb: Memory requirement in GB
        quantization: List of supported quantization levels
        recommended_partition_gb: Recommended partition size
    """
    config_path = Path(config_path)
    
    # Load existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'models' not in config:
        config['models'] = {}
    
    # Set defaults
    if quantization is None:
        quantization = ["fp16", "int8", "int4"]
    
    if recommended_partition_gb is None:
        # Add 25% overhead for recommended partition
        recommended_partition_gb = memory_gb * 1.25
    
    # Add model entry
    config['models'][model_id] = {
        'model_id': model_id,
        'parameters': parameters,
        'memory_gb': float(memory_gb),
        'quantization': quantization,
        'recommended_partition_gb': float(recommended_partition_gb),
    }
    
    # Write back to file
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Added model: {model_id}")
    print(f"  Parameters: {parameters}")
    print(f"  Memory: {memory_gb}GB")
    print(f"  Recommended partition: {recommended_partition_gb:.1f}GB")


def main():
    parser = argparse.ArgumentParser(
        description='Add model sizing entry to configuration'
    )
    parser.add_argument(
        '--config',
        default='model_sizing_config.yaml',
        help='Path to model sizing config file'
    )
    parser.add_argument(
        '--model',
        required=True,
        help='Model ID (e.g., "cohere/Command-R")'
    )
    parser.add_argument(
        '--params',
        required=True,
        help='Parameter count (e.g., "7B", "13B")'
    )
    parser.add_argument(
        '--memory',
        type=float,
        required=True,
        help='Memory requirement in GB'
    )
    parser.add_argument(
        '--quantization',
        nargs='+',
        default=['fp16', 'int8', 'int4'],
        help='Supported quantization levels'
    )
    parser.add_argument(
        '--recommended-partition',
        type=float,
        help='Recommended partition size in GB (default: memory * 1.25)'
    )
    
    args = parser.parse_args()
    
    add_model_entry(
        args.config,
        args.model,
        args.params,
        args.memory,
        args.quantization,
        args.recommended_partition
    )


if __name__ == '__main__':
    main()

