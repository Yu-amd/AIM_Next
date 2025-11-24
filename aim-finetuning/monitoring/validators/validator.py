"""
Validation framework for fine-tuning jobs.

Provides quality checks, model comparison, and test dataset validation.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    score: Optional[float] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None


@dataclass
class ModelComparison:
    """Comparison between base and fine-tuned models."""
    base_model_id: str
    finetuned_model_id: str
    loss_improvement: Optional[float] = None
    perplexity_base: Optional[float] = None
    perplexity_finetuned: Optional[float] = None
    accuracy_base: Optional[float] = None
    accuracy_finetuned: Optional[float] = None


class FineTuningValidator:
    """Validation framework for fine-tuning jobs."""
    
    def __init__(self, test_dataset_path: Optional[str] = None):
        """
        Initialize validator.
        
        Args:
            test_dataset_path: Path to test dataset for validation
        """
        self.test_dataset_path = test_dataset_path
        self.validation_results: List[ValidationResult] = []
    
    def validate_training_loss(
        self,
        train_loss: float,
        expected_range: Tuple[float, float] = (0.0, 10.0),
        decreasing: bool = True
    ) -> ValidationResult:
        """
        Validate training loss is within expected range.
        
        Args:
            train_loss: Final training loss
            expected_range: Expected (min, max) range for loss
            decreasing: Whether loss should be decreasing
            
        Returns:
            ValidationResult
        """
        min_loss, max_loss = expected_range
        passed = min_loss <= train_loss <= max_loss
        
        message = f"Training loss: {train_loss:.4f}"
        if not passed:
            message += f" (expected range: {min_loss}-{max_loss})"
        
        return ValidationResult(
            check_name="training_loss",
            passed=passed,
            score=train_loss,
            message=message
        )
    
    def validate_model_output(
        self,
        model_path: str,
        test_prompts: List[str],
        expected_keywords: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate model can generate outputs for test prompts.
        
        Args:
            model_path: Path to fine-tuned model
            test_prompts: List of test prompts
            expected_keywords: Optional keywords that should appear in outputs
            
        Returns:
            ValidationResult
        """
        if not TORCH_AVAILABLE:
            return ValidationResult(
                check_name="model_output",
                passed=False,
                message="PyTorch not available for model validation"
            )
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load model
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            model.eval()
            
            # Test generation
            successful_generations = 0
            total_prompts = len(test_prompts)
            
            for prompt in test_prompts:
                try:
                    inputs = tokenizer(prompt, return_tensors="pt")
                    with torch.no_grad():
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=50,
                            do_sample=False
                        )
                    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                    
                    # Check for expected keywords if provided
                    if expected_keywords:
                        if any(keyword.lower() in generated_text.lower() for keyword in expected_keywords):
                            successful_generations += 1
                    else:
                        successful_generations += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to generate for prompt: {e}")
            
            success_rate = successful_generations / total_prompts if total_prompts > 0 else 0
            passed = success_rate >= 0.8  # 80% success rate threshold
            
            return ValidationResult(
                check_name="model_output",
                passed=passed,
                score=success_rate,
                message=f"Generated outputs for {successful_generations}/{total_prompts} prompts ({success_rate*100:.1f}%)"
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="model_output",
                passed=False,
                message=f"Failed to validate model output: {str(e)}"
            )
    
    def validate_checkpoint_integrity(
        self,
        checkpoint_path: str
    ) -> ValidationResult:
        """
        Validate checkpoint files are complete and readable.
        
        Args:
            checkpoint_path: Path to checkpoint directory
            
        Returns:
            ValidationResult
        """
        checkpoint_dir = Path(checkpoint_path)
        
        if not checkpoint_dir.exists():
            return ValidationResult(
                check_name="checkpoint_integrity",
                passed=False,
                message=f"Checkpoint directory not found: {checkpoint_path}"
            )
        
        required_files = ["checkpoint_info.json", "training_state.json"]
        missing_files = []
        
        for file_name in required_files:
            file_path = checkpoint_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            return ValidationResult(
                check_name="checkpoint_integrity",
                passed=False,
                message=f"Missing required files: {', '.join(missing_files)}"
            )
        
        # Validate JSON files are readable
        try:
            with open(checkpoint_dir / "checkpoint_info.json", 'r') as f:
                json.load(f)
            with open(checkpoint_dir / "training_state.json", 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                check_name="checkpoint_integrity",
                passed=False,
                message=f"Invalid JSON in checkpoint files: {str(e)}"
            )
        
        return ValidationResult(
            check_name="checkpoint_integrity",
            passed=True,
            message="Checkpoint files are valid and complete"
        )
    
    def validate_aim_profile(
        self,
        profile_path: str
    ) -> ValidationResult:
        """
        Validate AIM profile is correctly formatted.
        
        Args:
            profile_path: Path to AIM profile JSON file
            
        Returns:
            ValidationResult
        """
        profile_file = Path(profile_path)
        
        if not profile_file.exists():
            return ValidationResult(
                check_name="aim_profile",
                passed=False,
                message=f"Profile file not found: {profile_path}"
            )
        
        try:
            with open(profile_file, 'r') as f:
                profile = json.load(f)
            
            # Check required fields
            required_fields = ["model_id", "base_model_id", "fine_tuning_method", "memory_gb"]
            missing_fields = [field for field in required_fields if field not in profile]
            
            if missing_fields:
                return ValidationResult(
                    check_name="aim_profile",
                    passed=False,
                    message=f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Validate memory_gb is positive
            if profile.get("memory_gb", 0) <= 0:
                return ValidationResult(
                    check_name="aim_profile",
                    passed=False,
                    message="memory_gb must be positive"
                )
            
            return ValidationResult(
                check_name="aim_profile",
                passed=True,
                message="AIM profile is valid"
            )
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                check_name="aim_profile",
                passed=False,
                message=f"Invalid JSON in profile: {str(e)}"
            )
    
    def compare_models(
        self,
        base_model_path: str,
        finetuned_model_path: str,
        test_dataset_path: Optional[str] = None
    ) -> ModelComparison:
        """
        Compare base and fine-tuned models.
        
        Args:
            base_model_path: Path to base model
            finetuned_model_path: Path to fine-tuned model
            test_dataset_path: Optional path to test dataset
            
        Returns:
            ModelComparison object
        """
        comparison = ModelComparison(
            base_model_id=base_model_path,
            finetuned_model_id=finetuned_model_path
        )
        
        # This would require loading both models and running evaluation
        # For now, return basic comparison structure
        logger.info(f"Comparing models: {base_model_path} vs {finetuned_model_path}")
        
        return comparison
    
    def run_all_checks(
        self,
        training_info: Dict[str, Any],
        model_path: str,
        checkpoint_path: Optional[str] = None,
        profile_path: Optional[str] = None
    ) -> List[ValidationResult]:
        """
        Run all validation checks.
        
        Args:
            training_info: Training information dictionary
            model_path: Path to fine-tuned model
            checkpoint_path: Optional path to checkpoint
            profile_path: Optional path to AIM profile
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        # Validate training loss
        if "results" in training_info and "train_loss" in training_info["results"]:
            loss_result = self.validate_training_loss(
                training_info["results"]["train_loss"]
            )
            results.append(loss_result)
        
        # Validate checkpoint if provided
        if checkpoint_path:
            checkpoint_result = self.validate_checkpoint_integrity(checkpoint_path)
            results.append(checkpoint_result)
        
        # Validate AIM profile if provided
        if profile_path:
            profile_result = self.validate_aim_profile(profile_path)
            results.append(profile_result)
        
        # Store results
        self.validation_results = results
        
        # Log summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        logger.info(f"Validation complete: {passed}/{total} checks passed")
        
        return results
    
    def generate_report(self) -> str:
        """
        Generate validation report.
        
        Returns:
            Formatted validation report string
        """
        if not self.validation_results:
            return "No validation results available"
        
        report = ["=== Fine-Tuning Validation Report ===\n"]
        
        for result in self.validation_results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            report.append(f"{status} - {result.check_name}")
            report.append(f"  {result.message}")
            if result.score is not None:
                report.append(f"  Score: {result.score:.4f}")
            report.append("")
        
        passed = sum(1 for r in self.validation_results if r.passed)
        total = len(self.validation_results)
        report.append(f"Summary: {passed}/{total} checks passed")
        
        return "\n".join(report)

