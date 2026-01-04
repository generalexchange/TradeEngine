"""Fill processing and validation.

Handles trade fills from brokers and validates them against orders.
"""

from typing import Optional

from trade_engine.execution.order_state import Order, OrderStatus


class Fill:
    """Represents a trade fill from a broker."""

    def __init__(
        self,
        broker_order_id: str,
        symbol: str,
        quantity: float,
        price: float,
        timestamp: str,
        fill_id: Optional[str] = None,
    ):
        """Initialize fill.

        Args:
            broker_order_id: Broker's order ID
            symbol: Trading symbol
            quantity: Filled quantity (positive)
            price: Fill price
            timestamp: Fill timestamp
            fill_id: Unique fill identifier
        """
        self.fill_id = fill_id or f"fill_{timestamp}"
        self.broker_order_id = broker_order_id
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.notional = quantity * price

    def to_dict(self) -> dict:
        """Convert fill to dictionary."""
        return {
            "fill_id": self.fill_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price": self.price,
            "notional": self.notional,
            "timestamp": self.timestamp,
        }


class FillProcessor:
    """Processes and validates fills from brokers."""

    @staticmethod
    def apply_fill_to_order(order: Order, fill: Fill) -> Order:
        """Apply a fill to an order, updating its state.

        Args:
            order: Order to update
            fill: Fill to apply

        Returns:
            Updated order
        """
        # Validate fill matches order
        if fill.symbol != order.symbol:
            raise ValueError(f"Fill symbol {fill.symbol} doesn't match order {order.symbol}")

        if fill.broker_order_id != order.broker_order_id:
            raise ValueError(
                f"Fill broker_order_id {fill.broker_order_id} doesn't match order"
            )

        # Update filled quantities
        new_filled_quantity = order.filled_quantity + fill.quantity
        new_filled_notional = order.filled_notional + fill.notional

        # Check if order is now fully filled
        if new_filled_quantity >= order.quantity:
            order.update_status(OrderStatus.FILLED)
            order.filled_quantity = order.quantity  # Cap at order quantity
            order.filled_notional = order.notional  # Cap at order notional
        else:
            order.update_status(OrderStatus.PARTIALLY_FILLED)
            order.filled_quantity = new_filled_quantity
            order.filled_notional = new_filled_notional

        # Update average fill price
        if order.filled_quantity > 0:
            order.average_fill_price = order.filled_notional / order.filled_quantity

        return order

    @staticmethod
    def validate_fill(fill: Fill, order: Order) -> tuple[bool, Optional[str]]:
        """Validate that a fill is legitimate for an order.

        Args:
            fill: Fill to validate
            order: Order to validate against

        Returns:
            (is_valid, error_message)
        """
        # Check symbol match
        if fill.symbol != order.symbol:
            return False, f"Symbol mismatch: {fill.symbol} != {order.symbol}"

        # Check broker order ID match
        if fill.broker_order_id != order.broker_order_id:
            return False, "Broker order ID mismatch"

        # Check quantity doesn't exceed order
        if order.filled_quantity + fill.quantity > order.quantity:
            return False, "Fill quantity exceeds remaining order quantity"

        # Check price is reasonable (basic sanity check)
        if fill.price <= 0:
            return False, "Fill price must be positive"

        return True, None

