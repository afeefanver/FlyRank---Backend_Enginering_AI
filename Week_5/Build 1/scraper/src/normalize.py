import re


def parse_price(price_text: str | None) -> float | None:
    """'£51.77' -> 51.77. Returns None if no number is found."""
    if not price_text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", price_text)
    return float(match.group()) if match else None
