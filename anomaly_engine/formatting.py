"""Indian-format number and currency helpers used in evidence strings."""

from __future__ import annotations

from datetime import date


def indian_digits(value: int) -> str:
    """Group digits in the Indian system: 3300000 -> '33,00,000'."""
    negative = value < 0
    s = str(abs(int(value)))
    if len(s) <= 3:
        out = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        out = ",".join(parts) + "," + tail
    return ("-" if negative else "") + out


def rupees(value: float | int | None) -> str:
    """Format an amount as '₹33,00,000'."""
    if value is None:
        return "Not recorded"
    return "₹" + indian_digits(round(value))


def rupees_words(value: float | int | None) -> str:
    """Short scale label: '₹33.00 lakh' / '₹1.25 crore'."""
    if value is None:
        return "Not recorded"
    value = float(value)
    if abs(value) >= 1_00_00_000:
        return f"₹{value / 1_00_00_000:.2f} crore"
    if abs(value) >= 1_00_000:
        return f"₹{value / 1_00_000:.2f} lakh"
    return rupees(value)


def pct(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "Not recorded"
    return f"{value:.{digits}f}%"


def signed_pct(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "Not recorded"
    return f"{value:+.{digits}f}%"


def pp(value: float | None, digits: int = 0) -> str:
    """Percentage points, used for progress gaps."""
    if value is None:
        return "Not recorded"
    return f"{value:.{digits}f} percentage points"


def human_date(value: date | str | None) -> str:
    if value is None or value == "":
        return "Not recorded"
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return str(value)
    return value.strftime("%d %b %Y")


def days(value: int | None) -> str:
    if value is None:
        return "Not recorded"
    if abs(value) == 1:
        return "1 day"
    return f"{value} days"
