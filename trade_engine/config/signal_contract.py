"""Signal contract validation and models.

Defines the strict contract that trading signals must adhere to.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Side(str, Enum):
    """Order side enumeration."""

    BUY = "BUY"
    SELL = "SELL"


class TimeHorizon(str, Enum):
    """Trading time horizon."""

    INTRADAY = "INTRADAY"
    SWING = "SWING"
    LONG = "LONG"


class SignalConstraints(BaseModel):
    """Signal execution constraints."""

    max_slippage_bps: int = Field(ge=0, le=1000, description="Max slippage in basis points")
    max_notional: Optional[float] = Field(
        default=None, gt=0, description="Maximum order notional in USD"
    )


class TradingSignal(BaseModel):
    """Trading signal contract - strict validation.

    This is the authoritative contract for all signals entering the Trade Engine.
    All fields are validated to ensure safety and correctness.
    """

    strategy_id: str = Field(..., min_length=1, description="Unique strategy identifier")
    symbol: str = Field(..., min_length=1, description="Trading symbol (e.g., 'AAPL')")
    side: Side = Field(..., description="Order side: BUY or SELL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence [0, 1]")
    target_exposure: float = Field(
        ..., gt=0, description="Target exposure in USD (absolute value)"
    )
    time_horizon: TimeHorizon = Field(..., description="Trading time horizon")
    constraints: SignalConstraints = Field(..., description="Execution constraints")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        # Basic validation - in production, validate against exchange symbol lists
        if not v.isalnum() and "." not in v:
            raise ValueError("Symbol must be alphanumeric or contain dots")
        return v.upper()

    def get_order_notional(self) -> float:
        """Calculate order notional from target exposure."""
        # If constraints specify max_notional, use the minimum
        if self.constraints.max_notional:
            return min(self.target_exposure, self.constraints.max_notional)
        return self.target_exposure

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "confidence": self.confidence,
            "target_exposure": self.target_exposure,
            "time_horizon": self.time_horizon.value,
            "constraints": {
                "max_slippage_bps": self.constraints.max_slippage_bps,
                "max_notional": self.constraints.max_notional,
            },
        }

