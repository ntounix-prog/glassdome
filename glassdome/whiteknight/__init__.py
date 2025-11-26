"""
WhiteKnight - Automated Vulnerability Validation

This module provides the Glassdome integration for WhiteKnight,
allowing Reaper to automatically validate deployed exploits.
"""

from .client import WhiteKnightClient, ValidationResult

__all__ = ["WhiteKnightClient", "ValidationResult"]

