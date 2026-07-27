from __future__ import annotations

from typing import Any
from urllib.request import build_opener


def open_with_current_network_settings(request: Any, timeout: float) -> Any:
    """Open one request without reusing urllib's process-global cached opener.

    urllib.request.urlopen lazily caches its opener, including the Windows proxy
    settings that were active during the first request in the process. Desktop
    proxy/TUN tools can change those settings while Oxo Tracker is running, so a
    fresh opener keeps connector traffic aligned with the machine's current
    network configuration.
    """

    return build_opener().open(request, timeout=timeout)
