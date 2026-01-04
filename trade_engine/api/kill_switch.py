"""Kill switch - emergency circuit breaker.

Global kill switch to halt all trading immediately.
State is maintained in external storage (Redis).
"""

from datetime import datetime
from typing import Optional


class KillSwitch:
    """Global kill switch for emergency trading halt.

    This is a critical safety mechanism that can halt all trading
    immediately, regardless of other system state.
    """

    def __init__(self, redis_client: Optional["Redis"] = None):
        """Initialize kill switch.

        Args:
            redis_client: Redis client for kill switch state
                          If None, uses in-memory fallback (not production-ready)
        """
        self.redis_client = redis_client
        self._memory_state: bool = False  # Fallback for testing

    async def is_active(self) -> bool:
        """Check if kill switch is active (trading halted).

        Returns:
            True if kill switch is active (trading halted)
        """
        if self.redis_client:
            # Check Redis for kill switch state
            state = await self.redis_client.get("kill_switch:active")
            return state == "1" if state else False
        else:
            # Fallback: in-memory state
            return self._memory_state

    async def activate(self, reason: str = "Manual activation"):
        """Activate kill switch (halt all trading).

        Args:
            reason: Reason for activation
        """
        if self.redis_client:
            await self.redis_client.set("kill_switch:active", "1")
            await self.redis_client.set("kill_switch:reason", reason)
            await self.redis_client.set("kill_switch:activated_at", str(datetime.now()))
        else:
            self._memory_state = True

    async def deactivate(self, reason: str = "Manual deactivation"):
        """Deactivate kill switch (resume trading).

        Args:
            reason: Reason for deactivation
        """
        if self.redis_client:
            await self.redis_client.set("kill_switch:active", "0")
            await self.redis_client.set("kill_switch:deactivated_at", str(datetime.now()))
            await self.redis_client.set("kill_switch:deactivation_reason", reason)
        else:
            self._memory_state = False

    async def get_status(self) -> dict:
        """Get kill switch status.

        Returns:
            Status dictionary with active state and metadata
        """
        is_active = await self.is_active()

        if self.redis_client:
            reason = await self.redis_client.get("kill_switch:reason") or "Unknown"
            activated_at = await self.redis_client.get("kill_switch:activated_at") or "Unknown"
            return {
                "active": is_active,
                "reason": reason,
                "activated_at": activated_at,
            }
        else:
            return {
                "active": is_active,
                "reason": "In-memory state",
                "activated_at": "N/A",
            }

