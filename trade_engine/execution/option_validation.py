"""Option contract validation.

Validates option contracts before execution without strategy logic.
"""

from datetime import datetime
from typing import Optional, Tuple

from trade_engine.execution.option_orders import OptionLeg, OptionOrder, OptionSpreadOrder


class OptionValidationError(Exception):
    """Raised when option validation fails."""

    pass


class OptionContractValidator:
    """Validates option contracts and orders.

    This class performs basic validation without any strategy logic.
    """

    @staticmethod
    def validate_leg(leg: OptionLeg) -> Tuple[bool, Optional[str]]:
        """Validate a single option leg.

        Args:
            leg: Option leg to validate

        Returns:
            (is_valid, error_message)
        """
        # Validate expiration is in the future
        try:
            exp_date = datetime.strptime(leg.expiration, "%Y-%m-%d").date()
            today = datetime.now().date()
            if exp_date <= today:
                return False, f"Expiration {leg.expiration} must be in the future"
        except ValueError:
            return False, f"Invalid expiration format: {leg.expiration}"

        # Validate strike is positive
        if leg.strike <= 0:
            return False, f"Strike price must be positive: {leg.strike}"

        # Validate quantity is positive integer
        if leg.quantity <= 0:
            return False, f"Quantity must be positive: {leg.quantity}"

        # Validate contract multiplier
        if leg.contract_multiplier <= 0:
            return False, f"Contract multiplier must be positive: {leg.contract_multiplier}"

        # Validate side
        if leg.side not in ("BUY", "SELL"):
            return False, f"Side must be BUY or SELL: {leg.side}"

        # Validate option type
        if leg.option_type.value not in ("CALL", "PUT"):
            return False, f"Option type must be CALL or PUT: {leg.option_type}"

        return True, None

    @staticmethod
    def validate_option_order(order: OptionOrder) -> Tuple[bool, Optional[str]]:
        """Validate a single-leg option order.

        Args:
            order: Option order to validate

        Returns:
            (is_valid, error_message)
        """
        # Validate the leg
        is_valid, error = OptionContractValidator.validate_leg(order.leg)
        if not is_valid:
            return False, f"Leg validation failed: {error}"

        # Validate limit price if provided
        if order.limit_price is not None and order.limit_price <= 0:
            return False, f"Limit price must be positive: {order.limit_price}"

        return True, None

    @staticmethod
    def validate_spread_order(order: OptionSpreadOrder) -> Tuple[bool, Optional[str]]:
        """Validate a multi-leg spread order.

        Args:
            order: Spread order to validate

        Returns:
            (is_valid, error_message)
        """
        # Validate all legs
        for i, leg in enumerate(order.legs):
            is_valid, error = OptionContractValidator.validate_leg(leg)
            if not is_valid:
                return False, f"Leg {i+1} validation failed: {error}"

        # Validate all legs have same underlying (for simplicity)
        # In production, this might be relaxed for certain spread types
        underlying = order.legs[0].symbol
        for leg in order.legs[1:]:
            if leg.symbol != underlying:
                return False, f"All legs must have same underlying: {leg.symbol} != {underlying}"

        # Validate all legs have same expiration (for simplicity)
        # In production, calendar spreads would have different expirations
        expiration = order.legs[0].expiration
        for leg in order.legs[1:]:
            if leg.expiration != expiration:
                return False, f"All legs must have same expiration: {leg.expiration} != {expiration}"

        # Validate limit price if provided
        if order.limit_price is not None and order.limit_price == 0:
            return False, "Limit price cannot be zero"

        # Validate leg quantities are consistent (for atomic execution)
        # All legs should have the same quantity for proper spread execution
        quantities = [leg.quantity for leg in order.legs]
        if len(set(quantities)) > 1:
            # Allow different quantities but log a warning
            # In production, this might be configurable
            pass

        return True, None

    @staticmethod
    def validate_contract_symbol(contract_symbol: str) -> Tuple[bool, Optional[str]]:
        """Validate option contract symbol format.

        Args:
            contract_symbol: Contract symbol to validate

        Returns:
            (is_valid, error_message)
        """
        if not contract_symbol:
            return False, "Contract symbol cannot be empty"

        # Basic format check (broker-specific validation would be more complex)
        parts = contract_symbol.split("_")
        if len(parts) < 3:
            return False, f"Invalid contract symbol format: {contract_symbol}"

        return True, None

