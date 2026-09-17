"""Generic value-formatting helpers shared across asset gateways.

Any asset priced in Rupiah (gold today; stock, mutual-fund later) needs the
same currency formatting, so it lives here instead of being duplicated in
each gateway's prompt module.
"""


def format_rupiah(amount: float) -> str:
    """Format a number as Indonesian Rupiah, e.g. 1985000 -> "Rp1.985.000".

    Uses the "Rp" prefix and dot thousands-separators used in Indonesian
    financial media - never the ISO code "IDR".
    """
    return f"Rp{amount:,.0f}".replace(",", ".")
