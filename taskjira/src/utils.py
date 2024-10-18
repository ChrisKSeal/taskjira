"""utils.py

Helper scripts for TaskJira"""

import contextlib
from typing import Optional

from passpy import Store


def get_password_from_store(
    store: Store,
    pass_key: str,
) -> Optional[str]:
    """Retrieve a key from a password store."""
    with contextlib.suppress(FileNotFoundError):
        return password.rstrip("\n") if (password := store.get_key(pass_key)) else None
    return None
