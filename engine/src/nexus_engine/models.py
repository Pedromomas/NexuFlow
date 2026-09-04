from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import StrEnum


class BoostProfile(StrEnum):
    AUTO = "auto"
    SAFE = "safe"
    ROBLOX = "roblox"
    RIOT_SAFE = "riot_safe"
    VALVE_SAFE = "valve_safe"
    AGGRESSIVE = "aggressive"
    PING = "ping"
    PC = "pc"
    COMPLETE = "complete"
    HARDCORE_SAFE = "hardcore_safe"
    UNKNOWN_SAFE = "unknown_safe"
    PROTECTED_SAFE = "protected_safe"


@dataclass(frozen=True, slots=True)
class Endpoint:
    id: str
    ip: str
    game_id: str
    pool_id: str
    region: str | None = None


@dataclass(frozen=True, slots=True)
class EndpointPool:
    id: str
    game_id: str
    interchangeable: bool
    endpoints: tuple[Endpoint, ...]


@dataclass(frozen=True, slots=True)
class GameDefinition:
    id: str
    display_name: str
    process_names: tuple[str, ...]
    install_hints: tuple[str, ...]
    pools: tuple[EndpointPool, ...]
    steam_paths: tuple[str, ...] = ()
    protection: str = "Conservador"
    catalog_source: str | None = None


@dataclass(slots=True)
class ProbeStats:
    endpoint: Endpoint
    samples_ms: list[float | None] = field(default_factory=list)

    @property
    def sent(self) -> int:
        return len(self.samples_ms)

    @property
    def successful_samples(self) -> list[float]:
        return [x for x in self.samples_ms if x is not None]

    @property
    def received(self) -> int:
        return len(self.successful_samples)

    @property
    def loss_fraction(self) -> float:
        return 1.0 if not self.sent else 1.0 - (self.received / self.sent)

    @property
    def median_ms(self) -> float:
        return float(statistics.median(self.successful_samples)) if self.successful_samples else math.inf

    @property
    def jitter_ms(self) -> float:
        return float(statistics.pstdev(self.successful_samples)) if len(self.successful_samples) >= 2 else 0.0

    @property
    def score(self) -> float:
        if not self.successful_samples:
            return math.inf
        return self.median_ms + self.jitter_ms * 1.5 + self.loss_fraction * 300.0

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint.id,
            "ip": self.endpoint.ip,
            "sent": self.sent,
            "received": self.received,
            "loss_percent": round(self.loss_fraction * 100, 2),
            "median_ms": None if math.isinf(self.median_ms) else round(self.median_ms, 2),
            "jitter_ms": round(self.jitter_ms, 2),
            "score": None if math.isinf(self.score) else round(self.score, 2),
        }


@dataclass(slots=True)
class RouteDecision:
    pool_id: str
    best_endpoint: Endpoint | None
    blocked_endpoints: list[Endpoint]
    reason: str

    def to_dict(self) -> dict:
        return {
            "pool_id": self.pool_id,
            "best_endpoint": None if self.best_endpoint is None else self.best_endpoint.ip,
            "blocked": [x.ip for x in self.blocked_endpoints],
            "reason": self.reason,
        }
