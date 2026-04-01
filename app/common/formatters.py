import re
from typing import Any


def format_phone_number(v: Any) -> Any:
    """
    Takes any string, strips non-digits, and returns (XXX) XXX-XXXX.
    If it's not a 10-digit number, it returns the raw string
    so the Regex validator can catch the error properly.
    """
    if not isinstance(v, str):
        return v

    # Strip everything except digits
    digits = re.sub(r"\D", "", v)

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return v  # Let the regex handle it if it's the wrong length
