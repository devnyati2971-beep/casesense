"""In-process state store for OAuth PKCE flows (single-instance dev).

Production multi-pod deployments store state in Redis via store_state_async;
the in-process dict is the single-node fallback and is still single-use + TTL
enforced at consumption time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

_pending_states: Dict[str, Tuple[str, datetime]] = {}
