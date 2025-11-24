"""
Traffic-level guardrails: rate limiting, quotas, and access control.

Non-ML guardrails for traffic management.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    max_context_length: int = 8192
    max_upload_size_mb: int = 10
    allowed_geos: Optional[list] = None
    business_hours_only: bool = False
    business_hours_start: int = 9  # 9 AM
    business_hours_end: int = 17  # 5 PM


class RateLimiter:
    """Rate limiter for traffic-level guardrails."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.request_counts: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self.blocked_users: set = set()
        
        logger.info("Rate limiter initialized")
    
    def check_rate_limit(
        self,
        user_id: str,
        api_key: Optional[str] = None,
        context_length: int = 0,
        upload_size_mb: float = 0.0,
        geo: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if request should be allowed based on rate limits.
        
        Args:
            user_id: User identifier
            api_key: Optional API key
            context_length: Request context length
            upload_size_mb: Upload size in MB
            geo: Geographic location
            
        Returns:
            Tuple of (allowed, message)
        """
        identifier = api_key or user_id
        now = time.time()
        
        # Check if user is blocked
        if identifier in self.blocked_users:
            return False, "User is blocked"
        
        # Check context length
        if context_length > self.config.max_context_length:
            return False, f"Context length {context_length} exceeds limit {self.config.max_context_length}"
        
        # Check upload size
        if upload_size_mb > self.config.max_upload_size_mb:
            return False, f"Upload size {upload_size_mb}MB exceeds limit {self.config.max_upload_size_mb}MB"
        
        # Check geo restrictions
        if self.config.allowed_geos and geo and geo not in self.config.allowed_geos:
            return False, f"Access not allowed from {geo}"
        
        # Check business hours
        if self.config.business_hours_only:
            current_hour = datetime.now().hour
            if not (self.config.business_hours_start <= current_hour < self.config.business_hours_end):
                return False, "Access only allowed during business hours"
        
        # Clean old entries
        self._clean_old_entries(identifier, now)
        
        # Check per-minute limit
        minute_requests = self.request_counts[identifier]['minute']
        if len(minute_requests) >= self.config.requests_per_minute:
            return False, f"Rate limit exceeded: {self.config.requests_per_minute} requests per minute"
        
        # Check per-hour limit
        hour_requests = self.request_counts[identifier]['hour']
        if len(hour_requests) >= self.config.requests_per_hour:
            return False, f"Rate limit exceeded: {self.config.requests_per_hour} requests per hour"
        
        # Check per-day limit
        day_requests = self.request_counts[identifier]['day']
        if len(day_requests) >= self.config.requests_per_day:
            return False, f"Rate limit exceeded: {self.config.requests_per_day} requests per day"
        
        # Record request
        self.request_counts[identifier]['minute'].append(now)
        self.request_counts[identifier]['hour'].append(now)
        self.request_counts[identifier]['day'].append(now)
        
        return True, "Allowed"
    
    def _clean_old_entries(self, identifier: str, now: float):
        """Clean old request entries."""
        # Remove entries older than 1 minute
        self.request_counts[identifier]['minute'] = [
            t for t in self.request_counts[identifier]['minute']
            if now - t < 60
        ]
        
        # Remove entries older than 1 hour
        self.request_counts[identifier]['hour'] = [
            t for t in self.request_counts[identifier]['hour']
            if now - t < 3600
        ]
        
        # Remove entries older than 1 day
        self.request_counts[identifier]['day'] = [
            t for t in self.request_counts[identifier]['day']
            if now - t < 86400
        ]
    
    def block_user(self, identifier: str):
        """Block a user/API key."""
        self.blocked_users.add(identifier)
        logger.warning(f"User {identifier} blocked")
    
    def unblock_user(self, identifier: str):
        """Unblock a user/API key."""
        self.blocked_users.discard(identifier)
        logger.info(f"User {identifier} unblocked")
    
    def get_stats(self, identifier: str) -> Dict:
        """Get rate limit statistics for a user."""
        self._clean_old_entries(identifier, time.time())
        return {
            "requests_last_minute": len(self.request_counts[identifier]['minute']),
            "requests_last_hour": len(self.request_counts[identifier]['hour']),
            "requests_last_day": len(self.request_counts[identifier]['day']),
            "limits": {
                "per_minute": self.config.requests_per_minute,
                "per_hour": self.config.requests_per_hour,
                "per_day": self.config.requests_per_day
            },
            "blocked": identifier in self.blocked_users
        }

