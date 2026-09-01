from __future__ import annotations

import base64
import json
import threading
from pathlib import Path

from .policy_feed import LOCAL_FEATURES, PolicyError, validate_feed
from .state import program_data_dir


# Release verification key only. The private Ed25519 key is intentionally kept
# outside the source tree and every distributable artifact.
POLICY_PUBLIC_KEY_B64 = "JH/q1rsg2O3iKifPyng0ku3/K6LEZhjnhr0qOO2L6dc="
MAX_POLICY_BYTES = 64 * 1024
_lock = threading.RLock()


class FeatureDisabledByPolicy(RuntimeError):
    pass


def _strict_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class PolicyRuntime:
    """Consume a locally cached, Ed25519-signed disable-only policy.

    Network fetching is intentionally outside the privileged engine. A future
    updater may replace ``policy.json`` atomically, but the engine accepts it
    only after signature, expiration and monotonic-version validation.
    """

    def __init__(
        self,
        cache_path: Path | None = None,
        state_path: Path | None = None,
        public_key: bytes | None = None,
    ) -> None:
        root = program_data_dir() / "policy"
        self.cache_path = cache_path or root / "policy.json"
        self.state_path = state_path or root / "accepted-version.json"
        self.public_key = public_key or base64.b64decode(POLICY_PUBLIC_KEY_B64, validate=True)

    def _minimum_version(self) -> int:
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            version = value.get("highest_accepted_version") if isinstance(value, dict) else None
            return int(version) if type(version) is int and version >= 0 else 0
        except (OSError, ValueError, json.JSONDecodeError):
            return 0

    def _remember(self, version: int) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"highest_accepted_version": int(version)}, separators=(",", ":")),
            encoding="utf-8",
        )
        tmp.replace(self.state_path)

    def status(self) -> dict:
        """Return local-safe policy state; invalid remote data never enables anything."""
        with _lock:
            if not self.cache_path.exists():
                return {
                    "active": False,
                    "source": "local_defaults",
                    "verified": False,
                    "version": self._minimum_version(),
                    "disabled_features": [],
                    "warnings": [],
                    "reason": "No signed cached policy is installed",
                }
            try:
                size = self.cache_path.stat().st_size
                if size <= 0 or size > MAX_POLICY_BYTES:
                    raise PolicyError("policy cache size is invalid")
                raw = self.cache_path.read_text(encoding="utf-8")
                document = json.loads(raw, object_pairs_hook=_strict_object)
                validated = validate_feed(
                    document,
                    self.public_key,
                    minimum_version=self._minimum_version(),
                )
                self._remember(int(validated["version"]))
                return {
                    "active": True,
                    "source": "signed_cache",
                    "verified": True,
                    "version": int(validated["version"]),
                    "disabled_features": list(validated["disabled_features"]),
                    "warnings": list(validated["warnings"]),
                    "reason": None,
                }
            except (OSError, UnicodeError, json.JSONDecodeError, PolicyError) as exc:
                return {
                    "active": False,
                    "source": "local_defaults",
                    "verified": False,
                    "version": self._minimum_version(),
                    "disabled_features": [],
                    "warnings": ["Signed policy cache was rejected; conservative local policy remains active."],
                    "reason": str(exc),
                }

    def feature_enabled(self, feature: str) -> bool:
        name = str(feature).strip().lower()
        if name not in LOCAL_FEATURES:
            raise ValueError(f"Unknown local policy feature: {name}")
        return name not in set(self.status()["disabled_features"])

    def assert_feature_enabled(self, feature: str) -> None:
        if not self.feature_enabled(feature):
            raise FeatureDisabledByPolicy(f"{feature} is disabled by the signed safety policy")


def policy_status() -> dict:
    return PolicyRuntime().status()


def feature_enabled(feature: str) -> bool:
    return PolicyRuntime().feature_enabled(feature)


def assert_feature_enabled(feature: str) -> None:
    PolicyRuntime().assert_feature_enabled(feature)
