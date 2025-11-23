"""
Resource Isolator for GPU Compute Isolation

This module provides compute resource isolation to prevent one model
from monopolizing GPU compute resources.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComputeLimits:
    """Compute resource limits for a partition."""
    partition_id: int
    max_compute_units: Optional[int] = None  # Maximum compute units
    min_compute_units: Optional[int] = None  # Minimum guaranteed compute units
    priority: int = 0  # Scheduling priority


class ResourceIsolator:
    """
    Resource isolator for GPU compute isolation.
    
    This class manages compute resource allocation and isolation
    to ensure fair resource sharing across partitions.
    """
    
    def __init__(self, gpu_id: int = 0):
        """
        Initialize resource isolator.
        
        Args:
            gpu_id: GPU device ID
        """
        self.gpu_id = gpu_id
        self.compute_limits: Dict[int, ComputeLimits] = {}
        self._initialized = False
    
    def initialize(
        self,
        total_compute_units: int,
        partition_ids: List[int]
    ) -> bool:
        """
        Initialize compute isolation.
        
        Args:
            total_compute_units: Total compute units on GPU
            partition_ids: List of partition IDs
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.warning("Isolator already initialized")
            return False
        
        # Calculate compute units per partition (equal distribution)
        units_per_partition = total_compute_units // len(partition_ids)
        
        for partition_id in partition_ids:
            self.compute_limits[partition_id] = ComputeLimits(
                partition_id=partition_id,
                max_compute_units=units_per_partition,
                min_compute_units=units_per_partition,
                priority=0,
            )
        
        self.total_compute_units = total_compute_units
        self._initialized = True
        
        logger.info(
            f"Initialized compute isolation: {units_per_partition} units "
            f"per partition ({len(partition_ids)} partitions)"
        )
        
        return True
    
    def set_partition_limits(
        self,
        partition_id: int,
        max_units: Optional[int] = None,
        min_units: Optional[int] = None,
        priority: int = 0
    ) -> bool:
        """
        Set compute limits for a partition.
        
        Args:
            partition_id: Partition ID
            max_units: Maximum compute units
            min_units: Minimum guaranteed compute units
            priority: Scheduling priority
        
        Returns:
            True if successful, False otherwise
        """
        if partition_id not in self.compute_limits:
            logger.error(f"Partition {partition_id} not found")
            return False
        
        limits = self.compute_limits[partition_id]
        
        if max_units is not None:
            if max_units > self.total_compute_units:
                logger.error(
                    f"Max units {max_units} exceeds total {self.total_compute_units}"
                )
                return False
            limits.max_compute_units = max_units
        
        if min_units is not None:
            if min_units > self.total_compute_units:
                logger.error(
                    f"Min units {min_units} exceeds total {self.total_compute_units}"
                )
                return False
            limits.min_compute_units = min_units
        
        limits.priority = priority
        
        logger.info(
            f"Updated partition {partition_id} limits: "
            f"min={limits.min_compute_units}, max={limits.max_compute_units}, "
            f"priority={priority}"
        )
        
        return True
    
    def get_partition_limits(self, partition_id: int) -> Optional[ComputeLimits]:
        """Get compute limits for a partition."""
        return self.compute_limits.get(partition_id)
    
    def get_environment_variables(self, partition_id: int) -> Dict[str, str]:
        """
        Get environment variables for compute isolation.
        
        This returns environment variables that should be set for
        a container running on a specific partition.
        
        Args:
            partition_id: Partition ID
        
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        # Set ROCR_VISIBLE_DEVICES if needed
        # (This would be set to the specific GPU device)
        env_vars['ROCR_VISIBLE_DEVICES'] = str(self.gpu_id)
        
        # Set compute unit limits if available
        limits = self.get_partition_limits(partition_id)
        if limits:
            if limits.max_compute_units:
                env_vars['ROCM_MAX_COMPUTE_UNITS'] = str(limits.max_compute_units)
            if limits.min_compute_units:
                env_vars['ROCM_MIN_COMPUTE_UNITS'] = str(limits.min_compute_units)
        
        # Set partition ID for reference
        env_vars['AIM_PARTITION_ID'] = str(partition_id)
        
        return env_vars
    
    def validate_limits(self) -> Tuple[bool, List[str]]:
        """
        Validate compute limits configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self._initialized:
            errors.append("Isolator not initialized")
            return False, errors
        
        # Check total allocation
        total_min = sum(
            limits.min_compute_units or 0
            for limits in self.compute_limits.values()
        )
        
        if total_min > self.total_compute_units:
            errors.append(
                f"Total minimum compute units {total_min} exceeds "
                f"available {self.total_compute_units}"
            )
        
        # Check individual limits
        for partition_id, limits in self.compute_limits.items():
            if limits.min_compute_units and limits.max_compute_units:
                if limits.min_compute_units > limits.max_compute_units:
                    errors.append(
                        f"Partition {partition_id}: min units "
                        f"{limits.min_compute_units} > max units "
                        f"{limits.max_compute_units}"
                    )
        
        return len(errors) == 0, errors

