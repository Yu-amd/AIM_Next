"""
CLI tool for validating fine-tuning jobs.

Validates training results, checkpoints, and AIM profiles.
"""

import argparse
import json
import logging
from pathlib import Path

from monitoring.validators.validator import FineTuningValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for validation tool."""
    parser = argparse.ArgumentParser(description="Validate fine-tuning job")
    parser.add_argument("--training-info", type=str, required=True,
                       help="Path to training_info.json")
    parser.add_argument("--model-path", type=str, required=True,
                       help="Path to fine-tuned model")
    parser.add_argument("--checkpoint-path", type=str,
                       help="Path to checkpoint directory")
    parser.add_argument("--profile-path", type=str,
                       help="Path to AIM profile JSON")
    parser.add_argument("--test-dataset", type=str,
                       help="Path to test dataset for validation")
    parser.add_argument("--output", type=str,
                       help="Path to save validation report")
    
    args = parser.parse_args()
    
    # Load training info
    training_info_path = Path(args.training_info)
    if not training_info_path.exists():
        logger.error(f"Training info file not found: {args.training_info}")
        return 1
    
    with open(training_info_path, 'r') as f:
        training_info = json.load(f)
    
    # Initialize validator
    validator = FineTuningValidator(test_dataset_path=args.test_dataset)
    
    # Run validation
    logger.info("Running validation checks...")
    results = validator.run_all_checks(
        training_info=training_info,
        model_path=args.model_path,
        checkpoint_path=args.checkpoint_path,
        profile_path=args.profile_path
    )
    
    # Generate report
    report = validator.generate_report()
    print(report)
    
    # Save report if output path provided
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        logger.info(f"Validation report saved to {args.output}")
    
    # Return exit code based on results
    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

