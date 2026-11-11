# AI contribution: 50% or more AI-generated
"""DRF quotas use a client address, never the changing TCP connection port."""

from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle as DRFAnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle


def _without_port(address: str) -> str:
    """Normalize IPv4:port and bracketed IPv6:port; preserve bare IPv6."""
    if address.startswith("[") and "]" in address:
        return address[1 : address.index("]")]
    if address.count(":") == 1:
        return address.split(":", 1)[0]
    return address


class AnonRateThrottle(DRFAnonRateThrottle):
    """Apply the anonymous quota after DRF selects the trusted client address."""

    def get_ident(self, request: Request) -> str:
        """Honor NUM_PROXIES before dropping a transport-specific port."""
        return _without_port(super().get_ident(request))


class UserRateThrottle(DRFUserRateThrottle):
    """Use account quotas for members and a stable client address for visitors."""

    def get_ident(self, request: Request) -> str:
        """Normalize the anonymous fallback without changing authenticated keys."""
        return _without_port(super().get_ident(request))
