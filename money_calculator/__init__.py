"""Coolie Sector 4: business finance and activation layer.

This package implements the architecture's actual Sector 4: the money calculator
and business manager that evaluates spend, margin, and activation risk before a
real action is authorized.
"""

from .controller import MoneyCalculatorController
from .models import (
    ActivationDecisionCode,
    ActivationProposal,
    SpendRecommendation,
)
from .service import MoneyCalculatorService

__all__ = [
    "ActivationDecisionCode",
    "ActivationProposal",
    "MoneyCalculatorController",
    "MoneyCalculatorService",
    "SpendRecommendation",
]
