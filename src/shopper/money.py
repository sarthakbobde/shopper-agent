"""Money is stored as whole paise (ADR-010) and turned into text in exactly one place: here.

Indian digit grouping puts the first comma after three digits and then every two:
₹1,23,456 rather than ₹123,456.
"""


def group_indian(rupees: int) -> str:
    """1234567 -> "12,34,567"."""
    digits = str(rupees)
    if len(digits) <= 3:
        return digits
    last_three = digits[-3:]
    rest = digits[:-3]
    pairs = []
    while len(rest) > 2:
        pairs.insert(0, rest[-2:])
        rest = rest[:-2]
    pairs.insert(0, rest)
    return ",".join(pairs) + "," + last_three


def format_inr(paise: int) -> str:
    """409900 -> "₹4,099"; 12345650 -> "₹1,23,456.50". Paise are shown only when not zero."""
    sign = "-" if paise < 0 else ""
    rupees, leftover = divmod(abs(paise), 100)
    text = f"{sign}₹{group_indian(rupees)}"
    if leftover:
        text += f".{leftover:02d}"
    return text
