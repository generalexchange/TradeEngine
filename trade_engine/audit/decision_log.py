"""Risk decision audit logging.

Logs all risk check decisions for full auditability.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class DecisionLogger:
    """Logs risk decisions for audit trail.

    All decisions are immutable and logged with full context.
    """

    def __init__(self, log_file: Optional[str] = None):
        """Initialize decision logger.

        Args:
            log_file: Optional file path for logging (default: stdout)
        """
        self.log_file = log_file
        self._log_buffer: list[dict] = []

    def log_risk_decision(
        self,
        signal_id: str,
        strategy_id: str,
        symbol: str,
        decision: str,  # APPROVED, REJECTED
        check_results: Dict[str, Any],
        errors: list[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a risk decision.

        Args:
            signal_id: Unique signal identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            decision: Decision (APPROVED/REJECTED)
            check_results: Results of all risk checks
            errors: List of error messages (if rejected)
            metadata: Additional metadata
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_id": signal_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "decision": decision,
            "check_results": check_results,
            "errors": errors,
            "metadata": metadata or {},
        }

        # In production, this would write to persistent storage
        # (database, log aggregation service, etc.)
        self._log_buffer.append(log_entry)

        # For now, print JSON (in production, use proper logging)
        log_line = json.dumps(log_entry, indent=2)
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(log_line + "\n")
        else:
            print(f"[DECISION] {log_line}")

    def get_recent_decisions(
        self, strategy_id: Optional[str] = None, limit: int = 100
    ) -> list[dict]:
        """Get recent decisions (for testing/debugging).

        Args:
            strategy_id: Optional strategy filter
            limit: Maximum number of decisions to return

        Returns:
            List of decision log entries
        """
        decisions = self._log_buffer[-limit:] if len(self._log_buffer) > limit else self._log_buffer

        if strategy_id:
            decisions = [d for d in decisions if d.get("strategy_id") == strategy_id]

        return decisions

