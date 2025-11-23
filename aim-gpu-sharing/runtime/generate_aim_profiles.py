#!/usr/bin/env python3
"""
Generate AIM profiles for all models with different precision levels.

This script generates AIM profile JSON files for each model variant
(FP16, INT8, INT4) based on the model sizing configuration.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aim_profile_generator import AIMProfileGenerator


def main():
    """Generate all AIM profiles."""
    # Determine output directory
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = Path(__file__).parent / "aim_profiles"
    
    print(f"Generating AIM profiles...")
    print(f"Output directory: {output_dir}")
    
    # Create generator
    generator = AIMProfileGenerator()
    
    # Generate all profiles
    all_profiles = generator.generate_all_profiles()
    
    # Count total profiles
    total_profiles = sum(len(profiles) for profiles in all_profiles.values())
    print(f"\nGenerated {total_profiles} profiles for {len(all_profiles)} models")
    
    # Save all profiles
    saved_paths = generator.save_all_profiles(output_dir)
    
    print(f"\nSaved {len(saved_paths)} profile files to {output_dir}")
    
    # Print summary
    print("\nProfile summary by model:")
    for model_id, profiles in all_profiles.items():
        print(f"  {model_id}:")
        for profile in profiles:
            print(f"    - {profile.variant_id}: {profile.memory_requirement_gb}GB ({profile.precision})")
    
    print(f"\n✓ All profiles generated successfully!")


if __name__ == '__main__':
    main()

