"""Prompt template for gold analysis.

Placeholder only - the real reasoning instructions (technical/fundamental
framework, tone, depth, etc.) will be filled in separately. This just wires
the plumbing: verified price in, JSON-shaped reasoning request out.
"""

from investment_agent.shared.base_models import PriceSnapshot


def build_gold_prompt(price_snapshot: PriceSnapshot) -> str:
    """Build the reasoning prompt sent to the Claude Agent SDK for gold."""
    return (
        "You are a financial analyst assistant specializing in gold for the "
        "Indonesian retail market (Antam/Pegadaian-style pricing).\n"
        f"Current gold price: {price_snapshot.price} {price_snapshot.currency} per gram "
        f"(as of {price_snapshot.as_of.isoformat()}, "
        f"24h change: {price_snapshot.change_pct}%).\n\n"
        "TODO: replace this placeholder with the real gold analysis prompt.\n\n"
        "Respond with ONLY a JSON object with these keys:\n"
        '  "key_drivers": list[str]\n'
        '  "technical_summary": str\n'
        '  "fundamental_summary": str\n'
        '  "recommendation": "BUY" | "SELL" | "NEUTRAL"\n'
        '  "confidence_level": float between 0 and 1\n'
        '  "risk_scenario": str\n'
    )
