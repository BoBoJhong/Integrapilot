"""API 速率限制（可透過 DISABLE_RATE_LIMIT=1 關閉，供測試使用）。"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["2000/minute"])


def rate_limit(limit_str: str):
    """套用 slowapi 限制；若設 DISABLE_RATE_LIMIT 則略過。"""

    def decorator(fn):
        if os.getenv("DISABLE_RATE_LIMIT"):
            return fn
        return limiter.limit(limit_str)(fn)

    return decorator
