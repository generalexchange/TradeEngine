"""Paper trading broker adapter.

Simulates order execution without real capital at risk.
Useful for testing and development.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from trade_engine.brokers.base import BrokerAdapter, BrokerError


class PaperBroker(BrokerAdapter):
    """Paper trading broker - simulates execution without real capital.

    This broker simulates realistic execution with:
    - Instant fills (market orders)
    - Simulated slippage
    - Order state tracking
    """

    def __init__(self, slippage_bps: int = 5):
        """Initialize paper broker.

        Args:
            slippage_bps: Simulated slippage in basis points
        """
        self.slippage_bps = slippage_bps
        self._orders: dict[str, dict] = {}
        self._fills: dict[str, list[dict]] = {}

    @property
    def broker_name(self) -> str:
        """Return broker name."""
        return "PAPER"

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        **kwargs,
    ) -> str:
        """Submit order (simulated).

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type (only MARKET supported for paper)
            **kwargs: Additional parameters

        Returns:
            Broker order ID
        """
        if order_type != "MARKET":
            raise BrokerError(f"Paper broker only supports MARKET orders, got {order_type}")

        broker_order_id = f"PAPER_{uuid4().hex[:8]}"

        # Simulate order submission delay
        await asyncio.sleep(0.01)

        # Store order
        self._orders[broker_order_id] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": "SUBMITTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # For paper trading, immediately fill market orders
        await self._simulate_fill(broker_order_id, symbol, side, quantity)

        return broker_order_id

    async def _simulate_fill(
        self, broker_order_id: str, symbol: str, side: str, quantity: float
    ):
        """Simulate order fill with slippage.

        Args:
            broker_order_id: Broker order ID
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
        """
        # Simulate execution delay
        await asyncio.sleep(0.05)

        # Get mock price (in production, would fetch from market data)
        base_price = self._get_mock_price(symbol)

        # Apply slippage
        slippage_multiplier = 1 + (self.slippage_bps / 10000) * (1 if side == "BUY" else -1)
        fill_price = base_price * slippage_multiplier

        # Create fill
        fill = {
            "fill_id": f"fill_{uuid4().hex[:8]}",
            "broker_order_id": broker_order_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": fill_price,
            "notional": quantity * fill_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store fill
        if broker_order_id not in self._fills:
            self._fills[broker_order_id] = []
        self._fills[broker_order_id].append(fill)

        # Update order status
        if broker_order_id in self._orders:
            self._orders[broker_order_id]["status"] = "FILLED"
            self._orders[broker_order_id]["filled_at"] = fill["timestamp"]

    def _get_mock_price(self, symbol: str) -> float:
        """Get mock price for a symbol (for testing).

        In production, this would fetch real market data.

        Args:
            symbol: Trading symbol

        Returns:
            Mock price
        """
        # Simple hash-based mock price for consistency
        mock_prices = {
            "AAPL": 175.50,
            "MSFT": 380.25,
            "GOOGL": 140.75,
            "TSLA": 250.00,
        }
        return mock_prices.get(symbol, 100.0)

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order.

        Args:
            broker_order_id: Broker order ID

        Returns:
            True if cancellation successful
        """
        if broker_order_id not in self._orders:
            raise BrokerError(f"Order not found: {broker_order_id}")

        order = self._orders[broker_order_id]
        if order["status"] in ("FILLED", "CANCELLED"):
            return False

        order["status"] = "CANCELLED"
        order["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        return True

    async def get_order_status(self, broker_order_id: str) -> dict:
        """Get order status.

        Args:
            broker_order_id: Broker order ID

        Returns:
            Order status dictionary
        """
        if broker_order_id not in self._orders:
            raise BrokerError(f"Order not found: {broker_order_id}")

        return self._orders[broker_order_id].copy()

    async def get_fills(self, broker_order_id: str) -> list[dict]:
        """Get fills for an order.

        Args:
            broker_order_id: Broker order ID

        Returns:
            List of fill dictionaries
        """
        return self._fills.get(broker_order_id, []).copy()

