"""
Secret scanner for detecting API keys, tokens, and sensitive information.

Uses pattern matching and entropy analysis similar to Gitleaks/TruffleHog.
"""

import re
import logging
import hashlib
from typing import Dict, List, Optional
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class SecretScanner(BaseChecker):
    """Scanner for secrets, API keys, and sensitive information."""
    
    def __init__(self):
        """Initialize secret scanner."""
        # Common secret patterns
        self.secret_patterns = {
            "api_key": [
                r'api[_-]?key["\s:=]+([A-Za-z0-9_\-]{20,})',
                r'apikey["\s:=]+([A-Za-z0-9_\-]{20,})',
            ],
            "aws_key": [
                r'AKIA[0-9A-Z]{16}',
                r'aws[_-]?access[_-]?key[_-]?id["\s:=]+(AKIA[0-9A-Z]{16})',
            ],
            "aws_secret": [
                r'aws[_-]?secret[_-]?access[_-]?key["\s:=]+([A-Za-z0-9/+=]{40})',
            ],
            "github_token": [
                r'ghp_[A-Za-z0-9]{36}',
                r'github[_-]?token["\s:=]+(ghp_[A-Za-z0-9]{36})',
            ],
            "private_key": [
                r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
                r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----',
            ],
            "password": [
                r'password["\s:=]+([^\s"\']{8,})',
                r'pwd["\s:=]+([^\s"\']{8,})',
            ],
            "token": [
                r'token["\s:=]+([A-Za-z0-9_\-]{20,})',
                r'bearer["\s]+([A-Za-z0-9_\-\.]{20,})',
            ],
        }
        
        self.compiled_patterns = {}
        for secret_type, patterns in self.secret_patterns.items():
            self.compiled_patterns[secret_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        logger.info("Secret scanner initialized")
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        entropy = 0.0
        for char in set(text):
            p = text.count(char) / len(text)
            entropy -= p * (p.bit_length() - 1) if p > 0 else 0
        
        return entropy
    
    def _is_high_entropy(self, text: str, threshold: float = 3.5) -> bool:
        """Check if text has high entropy (likely random/secret)."""
        if len(text) < 10:
            return False
        return self._calculate_entropy(text) > threshold
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """Check content for secrets."""
        if not content:
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message="Empty content"
            )
        
        detected_secrets = {}
        
        # Pattern matching
        for secret_type, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                found = pattern.findall(content)
                if found:
                    matches.extend(found if isinstance(found, list) else [found])
            
            # Filter by entropy for token-like secrets
            if secret_type in ["api_key", "token"]:
                matches = [m for m in matches if self._is_high_entropy(str(m))]
            
            if matches:
                detected_secrets[secret_type] = matches
        
        # Calculate confidence
        confidence = min(len(detected_secrets) * 0.4, 1.0) if detected_secrets else 0.0
        passed = confidence < threshold
        
        # Redact secrets
        redacted_content = content
        if detected_secrets:
            for secret_type, secrets in detected_secrets.items():
                for secret in secrets:
                    if isinstance(secret, tuple):
                        secret = secret[0] if secret else ""
                    redacted_content = redacted_content.replace(str(secret), f"[{secret_type.upper()}_REDACTED]")
        
        message = "No secrets detected" if passed else f"Secrets detected: {list(detected_secrets.keys())}"
        
        return GuardrailResult(
            passed=passed, guardrail_type=None, action=None,
            confidence=confidence, message=message,
            details={"detected_secrets": {k: len(v) for k, v in detected_secrets.items()}},
            redacted_content=redacted_content if detected_secrets else None
        )
    
    def get_name(self) -> str:
        return "secret_scanner"

