"""Order state machine and lifecycle management.

Defines the states an order can be in and valid transitions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"  # Created, awaiting submission
    SUBMITTED = "SUBMITTED"  # Sent to broker
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partially executed
    FILLED = "FILLED"  # Fully executed
    CANCELLED = "CANCELLED"  # Cancelled before fill
    REJECTED = "REJECTED"  # Rejected by broker or risk checks
    FAILED = "FAILED"  # Execution failed


class Order(BaseModel):
    """Order representation with full lifecycle tracking."""

    order_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    notional: float
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None  # Broker's order ID
    filled_quantity: float = 0.0
    filled_notional: float = 0.0
    average_fill_price: Optional[float] = None
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
        """Update order status with validation.

        Args:
            new_status: New status
            **kwargs: Additional fields to update
        """
        # Validate state transition
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

        # Update timestamps
        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = str(datetime.now())
        elif new_status == OrderStatus.FILLED:
            self.filled_at = str(datetime.now())
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = str(datetime.now())

        # Update other fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

