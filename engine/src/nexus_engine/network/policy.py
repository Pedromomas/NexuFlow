from __future__ import annotations

from ..models import EndpointPool, ProbeStats, RouteDecision


class SmartRoutePolicy:
    MIN_RESPONSES = 2

    def decide(self, pool: EndpointPool, stats: list[ProbeStats], strict: bool = False) -> RouteDecision:
        if not pool.interchangeable:
            return RouteDecision(pool.id, None, [], "Pool is not explicitly interchangeable")
        responders = [x for x in stats if x.received >= self.MIN_RESPONSES]
        if len(responders) < 2:
            return RouteDecision(pool.id, None, [], "Insufficient comparable ICMP responders; ICMP silence is not treated as failure")
        best = min(responders, key=lambda x: x.score)
        if best.loss_fraction > 0.20:
            return RouteDecision(pool.id, best.endpoint, [], "Measurements too unstable for safe steering")
        blocked = []
        for candidate in responders:
            if candidate.endpoint == best.endpoint:
                continue
            if strict:
                blocked.append(candidate.endpoint)
                continue
            latency_bad = candidate.score >= best.score + 25 and candidate.score >= best.score * 1.30
            loss_bad = candidate.loss_fraction >= .25 and candidate.loss_fraction - best.loss_fraction >= .20
            if latency_bad or loss_bad:
                blocked.append(candidate.endpoint)
        return RouteDecision(pool.id, best.endpoint, blocked, f"Best endpoint selected by latency/jitter/loss score: {best.endpoint.id}")
