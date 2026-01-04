"""Option order routing to broker adapters.

Routes option orders to appropriate broker adapters.
Extends the existing order router to support options.
"""

from typing import Optional, Tuple

from trade_engine.brokers.base import BrokerAdapter
from trade_engine.execution.option_orders import OptionOrder, OptionSpreadOrder
from trade_engine.execution.option_validation import (
    OptionContractValidator,
    OptionValidationError,
)
from trade_engine.execution.order_state import OrderStatus


class OptionOrderRouter:
    """Routes option orders to broker adapters.

    This is a stateless router - broker selection is deterministic.
    """

    def __init__(self, default_broker: BrokerAdapter):
        """Initialize router with default broker.

        Args:
            default_broker: Default broker adapter to use
        """
        self.default_broker = default_broker
        self._broker_map: dict[str, BrokerAdapter] = {}

    def register_broker(self, broker_id: str, broker: BrokerAdapter):
        """Register a broker adapter for specific routing.

        Args:
            broker_id: Broker identifier
            broker: Broker adapter instance
        """
        self._broker_map[broker_id] = broker

    def get_broker(self, order: OptionOrder | OptionSpreadOrder) -> BrokerAdapter:
        """Get appropriate broker for an option order.

        Args:
            order: Option order

        Returns:
            Broker adapter to use
        """
        # For now, use default broker
        # In production, implement routing logic here
        return self.default_broker

    async def submit_option_order(
        self, order: OptionOrder
    ) -> Tuple[OptionOrder, Optional[str]]:
        """Submit a single-leg option order.

        Args:
            order: Option order to submit

        Returns:
            (updated_order, error_message)
        """
        # Validate contract
        is_valid, error = OptionContractValidator.validate_option_order(order)
        if not is_valid:
            order.update_status(OrderStatus.REJECTED, rejection_reason=error)
            return order, error

        broker = self.get_broker(order)

        try:
            # Submit to broker
            broker_order_id = await broker.submit_option_order(
                leg=order.leg,
                limit_price=order.limit_price,
            )

            # Update order with broker response
            order.broker_order_id = broker_order_id
            order.update_status(OrderStatus.SUBMITTED)

            return order, None

        except Exception as e:
            # Mark order as failed
            order.update_status(OrderStatus.FAILED, rejection_reason=str(e))
            return order, str(e)

    async def submit_spread_order(
        self, order: OptionSpreadOrder
    ) -> Tuple[OptionSpreadOrder, Optional[str]]:
        """Submit a multi-leg spread order (atomic execution).

        Args:
            order: Spread order to submit

        Returns:
            (updated_order, error_message)
        """
        # Validate spread
        is_valid, error = OptionContractValidator.validate_spread_order(order)
        if not is_valid:
            order.update_status(OrderStatus.REJECTED, rejection_reason=error)
            return order, error

        broker = self.get_broker(order)

        try:
            # Submit to broker (atomic execution)
            broker_order_id = await broker.submit_option_spread(
                legs=order.legs,
                limit_price=order.limit_price,
            )

            # Update order with broker response
            order.broker_order_id = broker_order_id
            order.update_status(OrderStatus.SUBMITTED)

            return order, None

        except Exception as e:
            # Mark order as failed
            order.update_status(OrderStatus.FAILED, rejection_reason=str(e))
            return order, str(e)

    async def cancel_option_order(
        self, order: OptionOrder | OptionSpreadOrder
    ) -> Tuple[bool, Optional[str]]:
        """Cancel an option order.

        Args:
            order: Order to cancel

        Returns:
            (success, error_message)
        """
        if order.is_terminal():
            return False, f"Cannot cancel order in terminal state: {order.status}"

        if not order.broker_order_id:
            return False, "Order not yet submitted to broker"

        broker = self.default_broker

        try:
            await broker.cancel_order(order.broker_order_id)
            order.update_status(OrderStatus.CANCELLED)
            return True, None
        except Exception as e:
            return False, str(e)

