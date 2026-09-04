from __future__ import annotations

from urllib.parse import urlparse


# This is an executable contract, not only documentation. The desktop UI may
# talk to the loopback control plane; the engine may perform explicit network
# diagnostics to the neutral targets below. No analytics or advertising host
# is present.
LOCAL_API_ORIGINS = frozenset({
    "http://127.0.0.1:8000",
})

DIAGNOSTIC_TARGETS = frozenset({
    "1.1.1.1",
    "8.8.8.8",
    "9.9.9.9",
})

BOUNDED_TRANSFER_HOSTS = frozenset({"speed.cloudflare.com"})


def assert_local_api_url(url: str) -> str:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    if origin not in LOCAL_API_ORIGINS or not parsed.path.startswith("/api/v1/"):
        raise ValueError("Network allowlist rejected a non-local API destination")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Network allowlist rejected URL credentials or fragment")
    return url


def network_contract() -> dict:
    return {
        "schema": 1,
        "default": "deny",
        "local_api_origins": sorted(LOCAL_API_ORIGINS),
        "diagnostic_targets": sorted(DIAGNOSTIC_TARGETS),
        "dns_benchmark_servers": ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112"],
        "dns_benchmark_domains": ["example.com", "www.microsoft.com", "www.cloudflare.com"],
        "bounded_transfer_hosts": sorted(BOUNDED_TRANSFER_HOSTS),
        "bounded_transfer_requires_user_action": True,
        "bounded_transfer_max_bytes": 30 * 1024 * 1024,
        "analytics": False,
        "advertising": False,
        "remote_commands": False,
        "policy_feed": "local_signed_cache_only",
    }
