"""Order routing to broker adapters.

Routes orders to appropriate broker adapters based on configuration.
"""

from typing import Optional

from trade_engine.brokers.base import BrokerAdapter
from trade_engine.config.signal_contract import TradingSignal
from trade_engine.execution.order_state import Order, OrderStatus


class OrderRouter:
    """Routes orders to broker adapters.

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

    def get_broker(self, signal: TradingSignal) -> BrokerAdapter:
        """Get appropriate broker for a signal.

        In production, this could route based on:
        - Symbol exchange
        - Strategy preferences
        - Broker availability
        - Cost optimization

        Args:
            signal: Trading signal

        Returns:
            Broker adapter to use
        """
        # For now, use default broker
        # In production, implement routing logic here
        return self.default_broker

    async def submit_order(
        self, order: Order, signal: TradingSignal
    ) -> tuple[Order, Optional[str]]:
        """Submit order to appropriate broker.

        Args:
            order: Order to submit
            signal: Original trading signal

        Returns:
            (updated_order, error_message)
        """
        broker = self.get_broker(signal)

        try:
            # Submit to broker
            broker_order_id = await broker.submit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type="MARKET",  # Could be derived from signal
            )

            # Update order with broker response
            order.broker_order_id = broker_order_id
            order.update_status(OrderStatus.SUBMITTED)

            return order, None

        except Exception as e:
            # Mark order as failed
            order.update_status(OrderStatus.FAILED, rejection_reason=str(e))
            return order, str(e)

    async def cancel_order(self, order: Order) -> tuple[bool, Optional[str]]:
        """Cancel an order.

        Args:
            order: Order to cancel

        Returns:
            (success, error_message)
        """
        if order.is_terminal():
            return False, f"Cannot cancel order in terminal state: {order.status}"

        if not order.broker_order_id:
            return False, "Order not yet submitted to broker"

        # Get broker (in production, track which broker was used)
        broker = self.default_broker

        try:
            await broker.cancel_order(order.broker_order_id)
            order.update_status(OrderStatus.CANCELLED)
            return True, None
        except Exception as e:
            return False, str(e)

