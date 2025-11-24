"""
Dataset preprocessing for fine-tuning.

Handles conversation formatting, tokenization, and data preparation.
"""

from typing import List, Dict, Any, Optional, Callable
from transformers import PreTrainedTokenizer
from datasets import Dataset
import logging

logger = logging.getLogger(__name__)


class DatasetPreprocessor:
    """Preprocess datasets for fine-tuning."""
    
    def __init__(
        self,
        tokenizer: PreTrainedTokenizer,
        max_length: int = 2048,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize preprocessor.
        
        Args:
            tokenizer: Tokenizer instance
            max_length: Maximum sequence length
            system_prompt: Optional system prompt to prepend
        """
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.system_prompt = system_prompt
        
        # Set pad token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def preprocess_conversation(
        self,
        dataset: Dataset,
        instruction_field: str = "instruction",
        input_field: Optional[str] = None,
        output_field: str = "output"
    ) -> Dataset:
        """
        Preprocess conversation format dataset.
        
        Args:
            dataset: Input dataset
            instruction_field: Field name for instruction
            input_field: Optional field name for input (for instruction-input-output format)
            output_field: Field name for output
            
        Returns:
            Preprocessed dataset with 'text' and 'input_ids' fields
        """
        def format_conversation(example: Dict[str, Any]) -> Dict[str, Any]:
            """Format a single conversation example."""
            # Build prompt
            if input_field and input_field in example:
                prompt = f"{example[instruction_field]}\n\nInput: {example[input_field]}\n\nOutput: "
            else:
                prompt = f"{example[instruction_field]}\n\nOutput: "
            
            if self.system_prompt:
                prompt = f"System: {self.system_prompt}\n\n{prompt}"
            
            response = example[output_field]
            
            # Combine prompt and response
            text = prompt + response
            
            return {"text": text}
        
        logger.info("Formatting conversation dataset...")
        dataset = dataset.map(format_conversation, remove_columns=dataset.column_names)
        
        # Tokenize
        logger.info("Tokenizing dataset...")
        dataset = dataset.map(
            self._tokenize_function,
            batched=True,
            remove_columns=["text"],
            desc="Tokenizing"
        )
        
        return dataset
    
    def preprocess_text(
        self,
        dataset: Dataset,
        text_field: str = "text"
    ) -> Dataset:
        """
        Preprocess plain text dataset.
        
        Args:
            dataset: Input dataset
            text_field: Field name containing text
            
        Returns:
            Preprocessed dataset with tokenized fields
        """
        logger.info("Tokenizing text dataset...")
        dataset = dataset.map(
            lambda x: self._tokenize_function({text_field: x[text_field]}),
            batched=True,
            remove_columns=[text_field],
            desc="Tokenizing"
        )
        
        return dataset
    
    def _tokenize_function(self, examples: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Tokenize examples.
        
        Args:
            examples: Dictionary with text examples
            
        Returns:
            Tokenized examples
        """
        texts = examples.get("text", examples.get(list(examples.keys())[0]))
        
        # Tokenize
        tokenized = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors=None
        )
        
        # For causal LM, labels are same as input_ids
        tokenized["labels"] = tokenized["input_ids"].copy()
        
        return tokenized
    
    def split_train_eval(
        self,
        dataset: Dataset,
        eval_ratio: float = 0.1,
        seed: int = 42
    ) -> tuple[Dataset, Dataset]:
        """
        Split dataset into train and eval sets.
        
        Args:
            dataset: Full dataset
            eval_ratio: Ratio for evaluation set
            seed: Random seed
            
        Returns:
            Tuple of (train_dataset, eval_dataset)
        """
        split = dataset.train_test_split(test_size=eval_ratio, seed=seed)
        train_dataset = split["train"]
        eval_dataset = split["test"]
        
        logger.info(
            f"Split dataset: {len(train_dataset)} train, {len(eval_dataset)} eval"
        )
        
        return train_dataset, eval_dataset

