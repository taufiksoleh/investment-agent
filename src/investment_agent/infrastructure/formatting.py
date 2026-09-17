"""Generic value-formatting helpers shared across asset gateways.

Any asset priced in Rupiah (gold, mutual fund, stock later) needs the same
currency formatting and change-direction phrasing, so both live here
instead of being duplicated in each gateway's prompt module.
"""


def format_rupiah(amount: float) -> str:
    """Format a number as Indonesian Rupiah, e.g. 1985000 -> "Rp1.985.000".

    Uses the "Rp" prefix and dot thousands-separators used in Indonesian
    financial media - never the ISO code "IDR".
    """
    return f"Rp{amount:,.0f}".replace(",", ".")


def describe_change_pct(change_pct: float | None) -> str:
    """Describe a percent-point price change in Indonesian, e.g. "naik 1.20%"."""
    if change_pct is None:
        return "tidak tersedia"
    if change_pct > 0:
        return f"naik {change_pct:.2f}%"
    if change_pct < 0:
        return f"turun {abs(change_pct):.2f}%"
    return "stabil (0%)"
