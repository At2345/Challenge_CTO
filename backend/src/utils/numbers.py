import re
from decimal import Decimal
from typing import Any

GERMAN_NUM_RE = re.compile(r"^\s*-?\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*$")


def parse_decimal(val: Any) -> Decimal:
    """Convert numbers, or German/US formatted numeric strings, to Decimal.

    German format uses '.' as thousands separator and ',' as decimal
    separator (e.g. '1.234,56' -> 1234.56). Plain strings such as '1234.56'
    are also accepted.
    """
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, str):
        s = val.strip().replace("€", "").replace("EUR", "").strip()
        if GERMAN_NUM_RE.match(s):
            s = s.replace(".", "").replace(",", ".")
        return Decimal(s)
    raise TypeError(f"Unsupported type for Decimal conversion: {type(val)}")
