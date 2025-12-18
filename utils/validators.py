"""Input validation helpers."""
from typing import Tuple
import config


def validate_bet_amount(amount: int) -> Tuple[bool, str]:
    """Validate bet amount."""
    if amount < config.MIN_BET_AMOUNT:
        return False, f"Minimum bet amount is {config.MIN_BET_AMOUNT} bits."
    return True, ""


def validate_wager_options(options: list) -> Tuple[bool, str]:
    """Validate wager options."""
    if len(options) < 2:
        return False, "Wager must have at least 2 options."
    if len(options) > 10:
        return False, "Wager cannot have more than 10 options."
    if any(not option.strip() for option in options):
        return False, "All options must be non-empty."
    if len(set(options)) != len(options):
        return False, "All options must be unique."
    return True, ""


def validate_wager_title(title: str) -> Tuple[bool, str]:
    """Validate wager title."""
    if not title or not title.strip():
        return False, "Wager title cannot be empty."
    if len(title) > 200:
        return False, "Wager title cannot exceed 200 characters."
    return True, ""

