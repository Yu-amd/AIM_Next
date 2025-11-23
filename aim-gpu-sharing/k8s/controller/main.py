#!/usr/bin/env python3
"""
Main entry point for GPU Sharing Partition Controller

This is the entry point for the Kubernetes controller deployment.
"""

import os
import sys
import logging

# Add controller directory to path
sys.path.insert(0, os.path.dirname(__file__))

from partition_controller import main

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()

