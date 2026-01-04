"""Risk limit definitions and validation.

This module defines all risk limits enforced by the Trade Engine.
All limits are configurable and should be externalized in production.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskLimits:
    """Centralized risk limit configuration."""

    # Position limits
    max_position_size_usd: float = 1_000_000.0  # Max position size per symbol
    max_total_exposure_usd: float = 10_000_000.0  # Max total portfolio exposure
    max_single_asset_exposure_pct: float = 0.20  # 20% max per asset

    # Loss limits
    max_daily_loss_usd: float = 100_000.0  # Max daily loss
    max_daily_loss_pct: float = 0.05  # 5% max daily loss

    # Order limits
    max_order_notional_usd: float = 500_000.0  # Max single order size
    min_order_notional_usd: float = 1_000.0  # Min order size (anti-spam)

    # Rate limits
    max_orders_per_strategy_per_minute: int = 10
    max_orders_per_strategy_per_hour: int = 100

    # Slippage limits
    max_slippage_bps: int = 50  # 50 basis points default max slippage

    @classmethod
    def from_dict(cls, config: dict) -> "RiskLimits":
        """Create RiskLimits from dictionary (for external config loading)."""
        return cls(**{k: v for k, v in config.items() if hasattr(cls, k)})


# Global default limits instance
# In production, this should be loaded from external config/DB
DEFAULT_LIMITS = RiskLimits()

