"""Trade execution audit logging.

Logs all trade executions for full auditability.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from trade_engine.execution.order_state import Order


class TradeLogger:
    """Logs trade executions for audit trail.

    All trades are immutable and logged with full context.
    """

    def __init__(self, log_file: Optional[str] = None):
        """Initialize trade logger.

        Args:
            log_file: Optional file path for logging (default: stdout)
        """
        self.log_file = log_file
        self._log_buffer: list[dict] = []

    def log_order_created(self, order: Order, signal: Dict[str, Any]):
        """Log order creation.

        Args:
            order: Order object
            signal: Original trading signal
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ORDER_CREATED",
            "order_id": order.order_id,
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "notional": order.notional,
            "status": order.status.value,
            "signal": signal,
        }

        self._write_log(log_entry)

    def log_order_submitted(self, order: Order, broker_order_id: str):
        """Log order submission to broker.

        Args:
            order: Order object
            broker_order_id: Broker's order ID
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ORDER_SUBMITTED",
            "order_id": order.order_id,
            "broker_order_id": broker_order_id,
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
        }

        self._write_log(log_entry)

    def log_order_filled(
        self, order: Order, fill_quantity: float, fill_price: float, fill_notional: float
    ):
        """Log order fill.

        Args:
            order: Order object
            fill_quantity: Filled quantity
            fill_price: Fill price
            fill_notional: Fill notional
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ORDER_FILLED",
            "order_id": order.order_id,
            "broker_order_id": order.broker_order_id,
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
            "side": order.side,
            "fill_quantity": fill_quantity,
            "fill_price": fill_price,
            "fill_notional": fill_notional,
            "total_filled_quantity": order.filled_quantity,
            "total_filled_notional": order.filled_notional,
            "average_fill_price": order.average_fill_price,
            "status": order.status.value,
        }

        self._write_log(log_entry)

    def log_order_cancelled(self, order: Order, reason: Optional[str] = None):
        """Log order cancellation.

        Args:
            order: Order object
            reason: Cancellation reason
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ORDER_CANCELLED",
            "order_id": order.order_id,
            "broker_order_id": order.broker_order_id,
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
            "reason": reason,
        }

        self._write_log(log_entry)

    def log_order_rejected(self, order: Order, reason: str):
        """Log order rejection.

        Args:
            order: Order object
            reason: Rejection reason
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ORDER_REJECTED",
            "order_id": order.order_id,
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
            "reason": reason,
        }

        self._write_log(log_entry)

    def _write_log(self, log_entry: dict):
        """Write log entry to storage.

        Args:
            log_entry: Log entry dictionary
        """
        # In production, this would write to persistent storage
        # (database, log aggregation service, etc.)
        self._log_buffer.append(log_entry)

        # For now, print JSON (in production, use proper logging)
        log_line = json.dumps(log_entry, indent=2)
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(log_line + "\n")
        else:
            print(f"[TRADE] {log_line}")

    def get_recent_trades(
        self, strategy_id: Optional[str] = None, limit: int = 100
    ) -> list[dict]:
        """Get recent trades (for testing/debugging).

        Args:
            strategy_id: Optional strategy filter
            limit: Maximum number of trades to return

        Returns:
            List of trade log entries
        """
        trades = self._log_buffer[-limit:] if len(self._log_buffer) > limit else self._log_buffer

        if strategy_id:
            trades = [t for t in trades if t.get("strategy_id") == strategy_id]

        return trades

