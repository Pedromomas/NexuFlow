from __future__ import annotations

import pytest

from app.modules.route_selector import RouteSelectorService


def test_route_selector_rejects_single_endpoint():
    service = RouteSelectorService()
    with pytest.raises(ValueError):
        service._validated_ips(["1.1.1.1"])


def test_route_selector_normalizes_and_deduplicates_ipv4():
    service = RouteSelectorService()
    assert service._validated_ips(["1.1.1.1", "8.8.8.8", "1.1.1.1"]) == ["1.1.1.1", "8.8.8.8"]


def test_route_selector_rejects_ipv6_for_firewall_steering():
    service = RouteSelectorService()
    with pytest.raises(ValueError):
        service._validated_ips(["1.1.1.1", "2606:4700:4700::1111"])


def test_route_selector_hard_blocks_protected_games_before_any_probe():
    service = RouteSelectorService()
    with pytest.raises(ValueError, match="protected games"):
        service.apply_best(
            game_id="cs2",
            program=r"C:\\Games\\cs2.exe",
            ips=["1.1.1.1", "8.8.8.8"],
            attempts=2,
            interchangeable=True,
            confirmed=True,
        )
