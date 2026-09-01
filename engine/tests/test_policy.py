from nexus_engine.models import Endpoint, EndpointPool, ProbeStats
from nexus_engine.network.policy import SmartRoutePolicy


def ep(name: str, ip: str) -> Endpoint:
    return Endpoint(name, ip, "test", "pool")


def test_conservative_blocks_clearly_worse_endpoint():
    a, b = ep("good", "192.0.2.1"), ep("bad", "192.0.2.2")
    pool = EndpointPool("pool", "test", True, (a, b))
    decision = SmartRoutePolicy().decide(pool, [ProbeStats(a, [29, 30, 31, 30, 30]), ProbeStats(b, [79, 80, 83, 81, 82])])
    assert decision.best_endpoint == a
    assert decision.blocked_endpoints == [b]


def test_icmp_silence_is_unknown_not_bad():
    a, b = ep("reply", "192.0.2.1"), ep("silent", "192.0.2.2")
    pool = EndpointPool("pool", "test", True, (a, b))
    decision = SmartRoutePolicy().decide(pool, [ProbeStats(a, [30, 31, 30, 30, 29]), ProbeStats(b, [None] * 5)])
    assert decision.blocked_endpoints == []


def test_non_interchangeable_pool_never_blocks():
    a, b = ep("a", "192.0.2.1"), ep("b", "192.0.2.2")
    pool = EndpointPool("pool", "test", False, (a, b))
    decision = SmartRoutePolicy().decide(pool, [ProbeStats(a, [20] * 5), ProbeStats(b, [200] * 5)], strict=True)
    assert decision.blocked_endpoints == []
