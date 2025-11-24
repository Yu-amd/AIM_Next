"""
Piiranha PII detector - multilingual PII detection.

Uses iiiorg/piiranha-v1-detect-personal-information for comprehensive PII detection.
"""

import logging
from typing import Optional, Dict, List
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class PiiranhaPIIChecker(BaseChecker):
    """Piiranha-based PII checker."""
    
    def __init__(self, model_name: str = "iiiorg/piiranha-v1-detect-personal-information"):
        """
        Initialize Piiranha PII checker.
        
        Args:
            model_name: HuggingFace model name
        """
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load Piiranha model."""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            import torch
            
            logger.info(f"Loading Piiranha model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            
            self.model.eval()
            logger.info("Piiranha model loaded successfully")
        except ImportError:
            logger.warning("transformers not installed")
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.error(f"Failed to load Piiranha model: {e}")
            self.model = None
            self.tokenizer = None
    
    def check(self, content: str, threshold: float = 0.8, **kwargs) -> GuardrailResult:
        """Check content for PII using Piiranha."""
        if not content:
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message="Empty content"
            )
        
        if not self.model or not self.tokenizer:
            logger.warning("Model not available, allowing content")
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message="Model not available"
            )
        
        try:
            import torch
            
            # Tokenize
            inputs = self.tokenizer(
                content, return_tensors="pt", truncation=True,
                max_length=512, padding=True, return_offsets_mapping=True
            )
            
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items() if k != "offset_mapping"}
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**{k: v for k, v in inputs.items() if k != "offset_mapping"})
                predictions = torch.argmax(outputs.logits, dim=-1)[0]
                probs = torch.softmax(outputs.logits, dim=-1)[0]
            
            # Extract PII entities
            detected_pii = {}
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            offset_mapping = inputs.get("offset_mapping", [None])[0]
            
            current_entity = None
            current_start = None
            
            for i, (pred, prob) in enumerate(zip(predictions, probs)):
                label_id = pred.item()
                max_prob = prob[label_id].item()
                
                # Get label name (assuming standard NER format)
                if label_id > 0 and max_prob > threshold:  # Non-O label
                    if current_entity is None:
                        current_entity = label_id
                        current_start = i
                else:
                    if current_entity is not None:
                        # Extract entity text
                        entity_tokens = tokens[current_start:i]
                        entity_text = self.tokenizer.convert_tokens_to_string(entity_tokens)
                        entity_type = f"PII_{label_id}"
                        
                        if entity_type not in detected_pii:
                            detected_pii[entity_type] = []
                        detected_pii[entity_type].append(entity_text)
                        
                        current_entity = None
            
            # Calculate confidence
            confidence = min(len(detected_pii) * 0.3, 1.0) if detected_pii else 0.0
            passed = confidence < threshold
            
            # Redact if PII found
            redacted_content = content
            if detected_pii:
                for pii_type, entities in detected_pii.items():
                    for entity in entities:
                        redacted_content = redacted_content.replace(entity, f"[{pii_type}_REDACTED]")
            
            message = "No PII detected" if passed else f"PII detected: {list(detected_pii.keys())}"
            
            return GuardrailResult(
                passed=passed, guardrail_type=None, action=None,
                confidence=confidence, message=message,
                details={"detected_pii": detected_pii, "entity_count": sum(len(v) for v in detected_pii.values())},
                redacted_content=redacted_content if detected_pii else None
            )
        except Exception as e:
            logger.error(f"Error in Piiranha check: {e}")
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message=f"Error: {str(e)}"
            )
    
    def get_name(self) -> str:
        return "piiranha_pii"

