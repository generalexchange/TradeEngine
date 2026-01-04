"""Option fill processing and validation.

Handles option fills and enforces contract multipliers.
"""

from typing import Optional, Tuple

from trade_engine.execution.option_orders import OptionLeg, OptionOrder, OptionSpreadOrder
from trade_engine.execution.order_state import OrderStatus


class OptionFill:
    """Represents an option fill from a broker."""

    def __init__(
        self,
        broker_order_id: str,
        contract_symbol: str,
        quantity: int,  # Number of contracts
        price_per_contract: float,
        timestamp: str,
        fill_id: Optional[str] = None,
    ):
        """Initialize option fill.

        Args:
            broker_order_id: Broker's order ID
            contract_symbol: Option contract symbol
            quantity: Number of contracts filled (positive integer)
            price_per_contract: Price per contract (premium)
            timestamp: Fill timestamp
            fill_id: Unique fill identifier
        """
        self.fill_id = fill_id or f"option_fill_{timestamp}"
        self.broker_order_id = broker_order_id
        self.contract_symbol = contract_symbol
        self.quantity = quantity
        self.price_per_contract = price_per_contract
        self.timestamp = timestamp

    def get_notional(self, contract_multiplier: int = 100) -> float:
        """Calculate fill notional.

        Args:
            contract_multiplier: Contract multiplier (typically 100)

        Returns:
            Total notional value
        """
        return self.price_per_contract * self.quantity * contract_multiplier

    def to_dict(self) -> dict:
        """Convert fill to dictionary."""
        return {
            "fill_id": self.fill_id,
            "broker_order_id": self.broker_order_id,
            "contract_symbol": self.contract_symbol,
            "quantity": self.quantity,
            "price_per_contract": self.price_per_contract,
            "timestamp": self.timestamp,
        }


class OptionFillProcessor:
    """Processes and validates option fills."""

    @staticmethod
    def apply_fill_to_order(order: OptionOrder, fill: OptionFill) -> OptionOrder:
        """Apply a fill to a single-leg option order.

        Args:
            order: Option order to update
            fill: Fill to apply

        Returns:
            Updated order
        """
        # Validate fill matches order
        contract_symbol = order.leg.get_contract_symbol()
        if fill.contract_symbol != contract_symbol:
            raise ValueError(
                f"Fill contract {fill.contract_symbol} doesn't match order {contract_symbol}"
            )

        if fill.broker_order_id != order.broker_order_id:
            raise ValueError(
                f"Fill broker_order_id {fill.broker_order_id} doesn't match order"
            )

        # Update filled quantities
        new_filled_quantity = order.filled_quantity + fill.quantity

        # Check if order is now fully filled
        if new_filled_quantity >= order.leg.quantity:
            order.update_status(OrderStatus.FILLED)
            order.filled_quantity = order.leg.quantity  # Cap at order quantity
        else:
            order.update_status(OrderStatus.PARTIALLY_FILLED)
            order.filled_quantity = new_filled_quantity

        # Update average fill price
        if order.filled_quantity > 0:
            if order.filled_price is None:
                order.filled_price = fill.price_per_contract
            else:
                # Weighted average
                total_cost = (
                    order.filled_price * (order.filled_quantity - fill.quantity)
                    + fill.price_per_contract * fill.quantity
                )
                order.filled_price = total_cost / order.filled_quantity

        return order

    @staticmethod
    def apply_fill_to_spread(
        order: OptionSpreadOrder, fill: OptionFill, leg: OptionLeg
    ) -> OptionSpreadOrder:
        """Apply a fill to a spread order (one leg at a time).

        Args:
            order: Spread order to update
            fill: Fill to apply
            leg: The leg that was filled

        Returns:
            Updated spread order
        """
        contract_symbol = leg.get_contract_symbol()

        # Validate fill matches leg
        if fill.contract_symbol != contract_symbol:
            raise ValueError(
                f"Fill contract {fill.contract_symbol} doesn't match leg {contract_symbol}"
            )

        # Update leg fill
        current_filled = order.leg_fills.get(contract_symbol, 0)
        new_filled = current_filled + fill.quantity

        # Cap at leg quantity
        if new_filled > leg.quantity:
            new_filled = leg.quantity

        order.leg_fills[contract_symbol] = new_filled
        order.leg_fill_prices[contract_symbol] = fill.price_per_contract

        # Check if all legs are fully filled (atomic execution)
        if order.is_fully_filled():
            order.update_status(OrderStatus.FILLED)
        elif new_filled > 0:
            order.update_status(OrderStatus.PARTIALLY_FILLED)

        return order

    @staticmethod
    def validate_fill(
        fill: OptionFill, order: OptionOrder
    ) -> Tuple[bool, Optional[str]]:
        """Validate that a fill is legitimate for an order.

        Args:
            fill: Fill to validate
            order: Order to validate against

        Returns:
            (is_valid, error_message)
        """
        contract_symbol = order.leg.get_contract_symbol()
        if fill.contract_symbol != contract_symbol:
            return False, f"Contract symbol mismatch: {fill.contract_symbol} != {contract_symbol}"

        if fill.broker_order_id != order.broker_order_id:
            return False, "Broker order ID mismatch"

        if fill.quantity <= 0:
            return False, "Fill quantity must be positive"

        if order.filled_quantity + fill.quantity > order.leg.quantity:
            return False, "Fill quantity exceeds remaining order quantity"

        if fill.price_per_contract <= 0:
            return False, "Fill price must be positive"

        return True, None


class AssignmentEvent:
    """Represents an option assignment event.

    This is emitted when an option is assigned (no portfolio mutation).
    """

    def __init__(
        self,
        contract_symbol: str,
        quantity: int,
        assignment_price: float,  # Strike price
        timestamp: str,
        event_id: Optional[str] = None,
    ):
        """Initialize assignment event.

        Args:
            contract_symbol: Option contract symbol
            quantity: Number of contracts assigned
            assignment_price: Strike price at assignment
            timestamp: Assignment timestamp
            event_id: Unique event identifier
        """
        from uuid import uuid4

        self.event_id = event_id or str(uuid4())
        self.contract_symbol = contract_symbol
        self.quantity = quantity
        self.assignment_price = assignment_price
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": "ASSIGNMENT",
            "contract_symbol": self.contract_symbol,
            "quantity": self.quantity,
            "assignment_price": self.assignment_price,
            "timestamp": self.timestamp,
        }


class ExerciseEvent:
    """Represents an option exercise event.

    This is emitted when an option is exercised (no portfolio mutation).
    """

    def __init__(
        self,
        contract_symbol: str,
        quantity: int,
        exercise_price: float,  # Strike price
        timestamp: str,
        event_id: Optional[str] = None,
    ):
        """Initialize exercise event.

        Args:
            contract_symbol: Option contract symbol
            quantity: Number of contracts exercised
            exercise_price: Strike price at exercise
            timestamp: Exercise timestamp
            event_id: Unique event identifier
        """
        from uuid import uuid4

        self.event_id = event_id or str(uuid4())
        self.contract_symbol = contract_symbol
        self.quantity = quantity
        self.exercise_price = exercise_price
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": "EXERCISE",
            "contract_symbol": self.contract_symbol,
            "quantity": self.quantity,
            "exercise_price": self.exercise_price,
            "timestamp": self.timestamp,
        }

