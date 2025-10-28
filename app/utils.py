import re
from typing import Optional
import bleach


def sanitize_input(value: Optional[str]) -> str:
    """Sanitize a user-supplied string for safe display and search.

    - Strips HTML tags using bleach.clean(..., strip=True)
    - Removes obvious SQL metacharacters like '--' and ';'
    - Trims whitespace
    """
    if value is None:
        return ""
    # remove NULL bytes
    val = value.replace("\x00", "")
    # strip tags
    val = bleach.clean(val, strip=True)
    # remove common SQL comment and statement separators
    val = re.sub(r"(--|;)", "", val)
    return val.strip()
