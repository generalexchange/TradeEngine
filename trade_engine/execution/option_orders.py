"""Option order models and lifecycle management.

This module defines option-specific order types and their lifecycle.
No strategy logic, Greeks, or position tracking - pure execution models.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from trade_engine.execution.order_state import OrderStatus


class OptionType(str, Enum):
    """Option type enumeration."""

    CALL = "CALL"
    PUT = "PUT"


class OptionLeg(BaseModel):
    """Single option leg in a spread or standalone order.

    Represents one leg of an option position (e.g., one call or put).
    """

    symbol: str = Field(..., description="Underlying symbol (e.g., 'AAPL')")
    option_type: OptionType = Field(..., description="CALL or PUT")
    strike: float = Field(..., gt=0, description="Strike price")
    expiration: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    side: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Number of contracts")
    contract_multiplier: int = Field(
        default=100, description="Contract multiplier (typically 100 for US options)"
    )

    @field_validator("expiration")
    @classmethod
    def validate_expiration(cls, v: str) -> str:
        """Validate expiration date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Expiration must be in YYYY-MM-DD format")
        return v

    def get_contract_symbol(self) -> str:
        """Generate contract symbol (broker-specific format).

        This is a simplified version. In production, this would
        use broker-specific formatting (e.g., OCC format).
        """
        option_code = "C" if self.option_type == OptionType.CALL else "P"
        # Simplified format: SYMBOL_YYMMDD_C/P_STRIKE
        exp_short = self.expiration.replace("-", "")[2:]  # YYMMDD
        return f"{self.symbol}_{exp_short}_{option_code}_{int(self.strike * 1000)}"

    def get_notional(self, price_per_contract: float) -> float:
        """Calculate notional value for this leg.

        Args:
            price_per_contract: Price per contract (premium)

        Returns:
            Total notional (price * quantity * multiplier)
        """
        return price_per_contract * self.quantity * self.contract_multiplier


class OptionOrder(BaseModel):
    """Single-leg option order.

    Represents an order for a single option contract.
    """

    order_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    leg: OptionLeg = Field(..., description="Option leg")
    limit_price: Optional[float] = Field(
        default=None, gt=0, description="Limit price per contract (if limit order)"
    )
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    filled_quantity: int = 0  # Number of contracts filled
    filled_price: Optional[float] = None  # Average fill price per contract
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    rejection_reason: Optional[str] = None

    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        )

    def update_status(self, new_status: OrderStatus, **kwargs):
        """Update order status with validation."""
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.SUBMITTED,
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.SUBMITTED: [
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.PARTIALLY_FILLED: [
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
        }

        if (
            self.status in valid_transitions
            and new_status not in valid_transitions[self.status]
            and not self.is_terminal()
        ):
            raise ValueError(
                f"Invalid state transition: {self.status} -> {new_status}"
            )

        self.status = new_status

        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = str(datetime.now())
        elif new_status == OrderStatus.FILLED:
            self.filled_at = str(datetime.now())
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = str(datetime.now())

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_notional(self, price_per_contract: Optional[float] = None) -> float:
        """Get order notional value.

        Args:
            price_per_contract: Price per contract (uses limit_price if None)

        Returns:
            Total notional value
        """
        price = price_per_contract or self.limit_price or 0.0
        return self.leg.get_notional(price)


class OptionSpreadOrder(BaseModel):
    """Multi-leg option spread order (atomic execution).

    Represents a spread order where all legs must execute together.
    This ensures atomicity - either all legs fill or none do.
    """

    order_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    legs: List[OptionLeg] = Field(..., min_length=2, description="Option legs in the spread")
    limit_price: Optional[float] = Field(
        default=None, description="Net limit price for the spread"
    )
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    leg_fills: dict[str, int] = Field(
        default_factory=dict, description="Filled quantity per leg (by contract symbol)"
    )
    leg_fill_prices: dict[str, float] = Field(
        default_factory=dict, description="Fill price per leg (by contract symbol)"
    )
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    rejection_reason: Optional[str] = None

    @field_validator("legs")
    @classmethod
    def validate_legs(cls, v: List[OptionLeg]) -> List[OptionLeg]:
        """Validate spread legs."""
        if len(v) < 2:
            raise ValueError("Spread must have at least 2 legs")
        if len(v) > 4:
            raise ValueError("Spread cannot have more than 4 legs")
        return v

    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        )

    def is_fully_filled(self) -> bool:
        """Check if all legs are fully filled."""
        for leg in self.legs:
            contract_symbol = leg.get_contract_symbol()
            filled_qty = self.leg_fills.get(contract_symbol, 0)
            if filled_qty < leg.quantity:
                return False
        return True

    def update_status(self, new_status: OrderStatus, **kwargs):
        """Update order status with validation."""
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.SUBMITTED,
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.SUBMITTED: [
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.PARTIALLY_FILLED: [
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
        }

        if (
            self.status in valid_transitions
            and new_status not in valid_transitions[self.status]
            and not self.is_terminal()
        ):
            raise ValueError(
                f"Invalid state transition: {self.status} -> {new_status}"
            )

        self.status = new_status

        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = str(datetime.now())
        elif new_status == OrderStatus.FILLED:
            self.filled_at = str(datetime.now())
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = str(datetime.now())

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_net_notional(self) -> float:
        """Get net notional value of the spread.

        Returns:
            Net notional (sum of all leg notionals)
        """
        total = 0.0
        for leg in self.legs:
            contract_symbol = leg.get_contract_symbol()
            fill_price = self.leg_fill_prices.get(contract_symbol, 0.0)
            if fill_price == 0.0 and self.limit_price:
                # Use limit price as estimate if no fills yet
                fill_price = self.limit_price / len(self.legs)
            total += leg.get_notional(fill_price)
        return total

