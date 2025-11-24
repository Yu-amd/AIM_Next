"""
Dataset loading and preprocessing for fine-tuning.

Supports multiple formats: JSONL, CSV, HuggingFace Datasets.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import csv
import logging
from datasets import Dataset, load_dataset
from transformers import PreTrainedTokenizer

logger = logging.getLogger(__name__)


class DatasetLoader:
    """Load and prepare datasets for fine-tuning."""
    
    def __init__(self, dataset_path: str, format: str = "auto"):
        """
        Initialize dataset loader.
        
        Args:
            dataset_path: Path to dataset file or HuggingFace dataset identifier
            format: Dataset format ("jsonl", "csv", "hf", "auto")
        """
        self.dataset_path = dataset_path
        self.format = format
        self.dataset = None
        
    def load(self) -> Dataset:
        """
        Load dataset based on format.
        
        Returns:
            HuggingFace Dataset object
        """
        if self.format == "auto":
            self.format = self._detect_format()
        
        logger.info(f"Loading dataset from {self.dataset_path} (format: {self.format})")
        
        if self.format == "hf":
            # HuggingFace dataset
            self.dataset = load_dataset(self.dataset_path)
            if isinstance(self.dataset, dict):
                # If multiple splits, use 'train' by default
                self.dataset = self.dataset.get("train", list(self.dataset.values())[0])
        elif self.format == "jsonl":
            self.dataset = self._load_jsonl()
        elif self.format == "csv":
            self.dataset = self._load_csv()
        else:
            raise ValueError(f"Unsupported format: {self.format}")
        
        logger.info(f"Loaded dataset with {len(self.dataset)} examples")
        return self.dataset
    
    def _detect_format(self) -> str:
        """Auto-detect dataset format."""
        if self.dataset_path.startswith("hf://") or "/" in self.dataset_path and not Path(self.dataset_path).exists():
            return "hf"
        
        path = Path(self.dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")
        
        if path.suffix == ".jsonl":
            return "jsonl"
        elif path.suffix == ".csv":
            return "csv"
        else:
            # Try to infer from content
            with open(path, 'r') as f:
                first_line = f.readline()
                if first_line.strip().startswith("{"):
                    return "jsonl"
                else:
                    return "csv"
    
    def _load_jsonl(self) -> Dataset:
        """Load JSONL format dataset."""
        data = []
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON line: {e}")
        
        return Dataset.from_list(data)
    
    def _load_csv(self) -> Dataset:
        """Load CSV format dataset."""
        data = []
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        return Dataset.from_list(data)
    
    def validate(self, required_fields: List[str]) -> bool:
        """
        Validate dataset has required fields.
        
        Args:
            required_fields: List of required field names
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        if self.dataset is None:
            self.load()
        
        if len(self.dataset) == 0:
            raise ValueError("Dataset is empty")
        
        sample = self.dataset[0]
        missing_fields = [field for field in required_fields if field not in sample]
        
        if missing_fields:
            raise ValueError(
                f"Dataset missing required fields: {missing_fields}. "
                f"Available fields: {list(sample.keys())}"
            )
        
        logger.info(f"Dataset validation passed. Required fields: {required_fields}")
        return True

