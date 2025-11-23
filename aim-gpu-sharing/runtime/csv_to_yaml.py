#!/usr/bin/env python3
"""
Convert CSV model sizing data to YAML configuration.

Usage:
    1. Fill in model_sizes_template.csv with data from PDF
    2. Run: python3 csv_to_yaml.py
"""

import csv
import yaml
from pathlib import Path


def csv_to_yaml(csv_path: str, yaml_path: str):
    """
    Convert CSV model sizing data to YAML configuration.
    
    Args:
        csv_path: Path to CSV file
        yaml_path: Path to YAML config file
    """
    csv_path = Path(csv_path)
    yaml_path = Path(yaml_path)
    
    # Load existing YAML config
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'models' not in config:
        config['models'] = {}
    
    # Read CSV
    models_added = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip comment lines
            if row.get('model_id', '').startswith('#'):
                continue
            
            model_id = row['model_id'].strip()
            if not model_id:
                continue
            
            parameters = row['parameters'].strip()
            memory_gb = float(row['memory_gb'].strip())
            
            # Parse quantization
            quantization_str = row.get('quantization', 'fp16,int8,int4').strip()
            quantization = [q.strip() for q in quantization_str.split(',')]
            
            # Get recommended partition or calculate
            recommended = row.get('recommended_partition_gb', '').strip()
            if recommended:
                recommended_partition_gb = float(recommended)
            else:
                # Default: 25% overhead
                recommended_partition_gb = memory_gb * 1.25
            
            # Add to config
            config['models'][model_id] = {
                'model_id': model_id,
                'parameters': parameters,
                'memory_gb': memory_gb,
                'quantization': quantization,
                'recommended_partition_gb': recommended_partition_gb,
            }
            
            models_added += 1
            print(f"Added: {model_id} ({parameters}) - {memory_gb}GB")
    
    # Write back to YAML
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\nAdded {models_added} models to {yaml_path}")


if __name__ == '__main__':
    import sys
    
    csv_path = Path(__file__).parent / 'model_sizes_template.csv'
    yaml_path = Path(__file__).parent / 'model_sizing_config.yaml'
    
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        yaml_path = Path(sys.argv[2])
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    if not yaml_path.exists():
        print(f"Error: YAML file not found: {yaml_path}")
        sys.exit(1)
    
    csv_to_yaml(csv_path, yaml_path)

