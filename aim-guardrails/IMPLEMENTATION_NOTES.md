# Guardrail Implementation Notes

## Current Implementation Approach

The current guardrail implementation uses **pattern-based detection** (regex patterns and heuristics), not machine learning models. This is a lightweight, fast approach suitable for prototyping and basic use cases.

### Why Pattern-Based?

1. **Fast**: No model loading or inference overhead
2. **Lightweight**: Minimal dependencies
3. **Deterministic**: Predictable behavior
4. **Easy to deploy**: No GPU requirements
5. **Good for structured data**: PII detection works well with patterns

### Limitations

1. **Toxicity Detection**: 
   - May miss nuanced toxic content
   - Can have false positives/negatives
   - Doesn't understand context

2. **PII Detection**:
   - Works well for structured formats (email, phone)
   - May miss unstructured PII (names in context)
   - Can't detect PII in images

3. **Prompt Injection**:
   - Pattern-based detection can be bypassed
   - May miss sophisticated injection attempts
   - Limited understanding of context

## Enhancement Options

### Option 1: Add ML-Based Checkers (Recommended for Production)

You can enhance the implementation with ML models:

#### Toxicity Detection
- **Detoxify**: Pre-trained toxicity classification model
  ```python
  from detoxify import Detoxify
  model = Detoxify('original')
  results = model.predict(text)
  ```

- **Perspective API**: Google's toxicity API
- **HuggingFace Models**: `unitary/toxic-bert`, `martin-ha/toxic-comment-model`

#### PII Detection
- **spaCy NER**: Named Entity Recognition
  ```python
  import spacy
  nlp = spacy.load("en_core_web_sm")
  doc = nlp(text)
  # Extract PERSON, EMAIL, PHONE, etc.
  ```

- **Presidio**: Microsoft's PII detection library
- **HuggingFace NER Models**: `dslim/bert-base-NER`

#### Prompt Injection
- **Fine-tuned classifiers**: Train on prompt injection datasets
- **Semantic similarity**: Compare against known injection patterns
- **LLM-based detection**: Use a small LLM to detect injection attempts

### Option 2: Hybrid Approach

Combine pattern-based and ML-based detection:

```python
class EnhancedToxicityChecker(BaseChecker):
    def __init__(self):
        # Pattern-based (fast, first pass)
        self.pattern_checker = ToxicityChecker()
        
        # ML-based (accurate, second pass)
        try:
            from detoxify import Detoxify
            self.ml_model = Detoxify('original')
        except ImportError:
            self.ml_model = None
    
    def check(self, content: str, threshold: float = 0.7, **kwargs):
        # Fast pattern check first
        pattern_result = self.pattern_checker.check(content, threshold)
        
        # If pattern check passes but we have ML model, use it
        if pattern_result.passed and self.ml_model:
            ml_results = self.ml_model.predict(content)
            toxicity_score = max(ml_results.values())
            
            if toxicity_score > threshold:
                return GuardrailResult(
                    passed=False,
                    confidence=toxicity_score,
                    message=f"ML model detected toxicity: {toxicity_score:.2f}"
                )
        
        return pattern_result
```

### Option 3: External Services

Use external APIs for guardrail checking:

- **Perspective API** (Google) - Toxicity detection
- **AWS Comprehend** - PII detection
- **Azure Content Moderator** - Content moderation
- **OpenAI Moderation API** - Content moderation

## Implementation Recommendations

### For Prototyping (Current)
✅ Pattern-based detection is sufficient
- Fast iteration
- No dependencies
- Easy to test

### For Production
✅ Use ML models or external services
- Better accuracy
- Context understanding
- Handles edge cases

### Hybrid Approach (Best of Both)
✅ Combine both:
- Pattern-based for fast filtering
- ML-based for accurate detection
- Fallback to patterns if ML unavailable

## Adding ML Models

To add ML-based checkers:

1. **Install dependencies**:
   ```bash
   pip install detoxify spacy transformers torch
   python -m spacy download en_core_web_sm
   ```

2. **Create ML-based checker**:
   ```python
   # guardrails/types/ml_toxicity_checker.py
   from guardrails.types.base_checker import BaseChecker
   from detoxify import Detoxify
   
   class MLToxicityChecker(BaseChecker):
       def __init__(self):
           self.model = Detoxify('original')
       
       def check(self, content: str, threshold: float = 0.7, **kwargs):
           results = self.model.predict(content)
           max_toxicity = max(results.values())
           
           return GuardrailResult(
               passed=max_toxicity < threshold,
               confidence=max_toxicity,
               message=f"Toxicity score: {max_toxicity:.2f}"
           )
   ```

3. **Update service to use ML checkers**:
   ```python
   # In guardrail_service.py
   from guardrails.types.ml_toxicity_checker import MLToxicityChecker
   self.guardrails[GuardrailType.TOXICITY] = MLToxicityChecker()
   ```

## Performance Considerations

- **Pattern-based**: ~1ms per check, no GPU needed
- **ML-based**: ~10-100ms per check, may need GPU for large models
- **External API**: ~100-500ms per check, network latency

Choose based on your latency requirements and accuracy needs.

