from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

from .anti_cheat import (
    anti_cheat_policy_report,
    boost_objective,
    effective_profile,
    is_protected_game,
    running_protected_games,
)
from .catalog import GameCatalog
from .hardware.health import gaming_health
from .hardware.memory import purge_standby_list
from .hardware.nvidia import nvidia_telemetry
from .hardware.power import PowerPlanManager
from .hardware.process import ProcessOptimizer
from .hardware.services import ServiceManager
from .history import SessionHistory
from .models import BoostProfile
from .network.dns import DNSManager
from .network.firewall import FirewallManager
from .network.icmp import probe_many
from .network.interfaces import InterfaceManager
from .network.mtu import MTUManager
from .network.policy import SmartRoutePolicy
from .network.quality import QualityStore, current_quality
from .network.route_diagnostics import trace_route
from .network.tcp_tweaks import TcpTweaks
from .state import StateStore, pending_manual_state


class NexusOrchestrator:
    def __init__(self):
        self.catalog = GameCatalog.load()
        self.state_store = StateStore()
        self.quality_store = QualityStore()
        self.history = SessionHistory()
        self.dns = DNSManager()
        self.mtu = MTUManager()
        self.firewall = FirewallManager()
        self.route_policy = SmartRoutePolicy()
        self.power = PowerPlanManager()
        self.services = ServiceManager()

    def _checkpoint(self, state: dict, key: str, value: Any) -> None:
        state[key] = value
        self.state_store.save(state)

    @staticmethod
    def _anti_cheat_safe(profile: BoostProfile) -> bool:
        return profile in {BoostProfile.RIOT_SAFE, BoostProfile.VALVE_SAFE, BoostProfile.PROTECTED_SAFE, BoostProfile.UNKNOWN_SAFE}

    @classmethod
    def _state_is_protected(cls, state: dict) -> bool:
        """Use both the persisted policy result and current runtime signals."""
        try:
            profile = BoostProfile(str(state.get("profile") or ""))
        except ValueError:
            profile = None
        return bool((profile is not None and cls._anti_cheat_safe(profile)) or running_protected_games())

    def optimize_game(self, game: dict, profile: BoostProfile) -> dict:
        if os.name != "nt":
            raise RuntimeError("System optimization is Windows-only")
        if not game.get("running") or not game.get("pid"):
            raise RuntimeError("Selected game is not running")

        requested_profile = profile
        profile = effective_profile(requested_profile, game.get("id"))
        protected = self._anti_cheat_safe(profile)
        objective_mode = boost_objective(requested_profile)
        hardcore = objective_mode == "hardcore_safe"
        network_requested = objective_mode in {"ping", "complete"}
        pc_requested = objective_mode in {"pc", "complete"}
        network_mutations = network_requested and not protected and not hardcore
        process_mutations = pc_requested and not protected and not hardcore
        power_plan_allowed = pc_requested and not hardcore

        # Protected titles do not need their executable path because NexuFlow
        # deliberately avoids game-process and firewall manipulation for them.
        if not protected and not game.get("executable"):
            raise RuntimeError("Could not resolve the running game's executable path")

        # Never stack sessions. Restore an interrupted/older BOOST snapshot first.
        old = self.state_store.load()
        if old.get("active"):
            self.restore_all()

        pending_manual = pending_manual_state()
        if pending_manual:
            raise RuntimeError(
                "Manual NexuFlow changes are pending rollback: " + ", ".join(pending_manual)
                + ". Restore them before starting BOOST."
            )

        boost_requested_at = time.time()
        anti_cheat = anti_cheat_policy_report(game.get("id"), requested_profile, profile)
        # Maximum compatibility: protected titles avoid PowerShell-based adapter
        # introspection while the game is running. Valve explicitly lists
        # PowerShell as software that can contribute to a VAC-secure connection
        # error. Native ICMP/UDP quality diagnostics do not need adapter handles.
        interface = None if protected or hardcore or not network_requested else InterfaceManager.primary_ipv4()

        # Prefer the rolling 20-30 s pre-BOOST window produced by the observer.
        # On a cold start, wait only until enough pre-mutation samples exist; no
        # system change happens during this warm-up.
        quality_before = self.quality_store.snapshot(30.0)
        baseline_deadline = time.time() + 20.0
        while not quality_before.get("complete_window") and time.time() < baseline_deadline:
            time.sleep(1.0)
            quality_before = self.quality_store.snapshot(30.0)
        if quality_before.get("sample_count", 0) == 0:
            quality_before = current_quality(window_seconds=30.0)

        started_at = time.time()
        state: dict = {
            "schema": 2,
            "session_id": str(uuid.uuid4()),
            "active": True,
            "started_at": started_at,
            "boost_requested_at": boost_requested_at,
            "profile": profile.value,
            "requested_profile": requested_profile.value,
            "objective_mode": objective_mode,
            "anti_cheat": anti_cheat,
            # Backward-compatible key for older UI/readers.
            "riot_safe": anti_cheat if anti_cheat.get("provider") == "Riot Vanguard" else None,
            "game": {
                "id": game["id"],
                "display_name": game["display_name"],
                "pid": int(game["pid"]),
                "executable": game.get("executable"),
            },
            "interface": (
                {"deferred": True, "reason": "protected_game_no_powershell"}
                if protected or hardcore or not network_requested
                else {"index": interface.index, "guid": interface.guid, "alias": interface.alias}
            ),
            "quality_before": quality_before,
            "quality_after": None,
            "adaptive_events": [],
            "gaming_health_before": gaming_health(protected_runtime=protected),
            "firewall_rules": [],
            "warnings": [],
        }
        self.state_store.save(state)

        report: dict = {
            "session_id": state["session_id"],
            "game": state["game"],
            "profile": profile.value,
            "requested_profile": requested_profile.value,
            "objective_mode": objective_mode,
            "anti_cheat": anti_cheat,
            "quality_before": quality_before,
            "network": {},
            "hardware": {},
            "warnings": state["warnings"],
        }

        # Protected titles never query the active adapter/current DNS through
        # PowerShell while the game is running. We can still compare public DNS
        # resolvers using direct UDP packets, and PMTU using native ICMP, but
        # both remain diagnostic-only and are never applied mid-session.
        if not network_requested:
            report["network"]["mode"] = {"skipped": True, "reason": "PC mode: network changes and diagnostics were not requested"}
        elif protected or hardcore:
            try:
                scores = asyncio.run(self.dns.benchmark([]))
                public_winner = min(
                    (score for score in scores if score.median_ms is not None and score.success_rate >= 0.75),
                    key=lambda score: score.score,
                    default=None,
                )
                report["network"]["dns"] = {
                    "changed": False,
                    "selected": "unchanged",
                    "recommended_public_resolver": public_winner.provider.name if public_winner else None,
                    "diagnostic_only": True,
                    "current_resolver_queried": False,
                    "reason": "Safe Core diagnostic-only: no adapter query or resolver change",
                    "benchmarks": [score.to_dict() for score in scores],
                }
            except Exception as exc:
                state["warnings"].append(f"Protected DNS diagnostic skipped: {exc}")

            try:
                mtu_result = self.mtu.recommend(1500)
                report["network"]["mtu"] = {
                    **mtu_result,
                    "apply": False,
                    "changed": False,
                    "diagnostic_only": True,
                    "current_interface_mtu_queried": False,
                    "reason": "Safe Core diagnostic-only: PMTU recommendation only",
                }
            except Exception as exc:
                state["warnings"].append(f"Protected PMTU diagnostic skipped: {exc}")
            self.state_store.save(state)
        else:
            # Normal/Roblox profiles may inspect and tune the active interface.
            if interface.probably_virtual or interface.network_category == "DomainAuthenticated":
                report["network"]["dns"] = {"changed": False, "reason": "VPN/virtual/domain-managed interface"}
            else:
                try:
                    dns_snapshot = self.dns.snapshot(interface.index, interface.guid)
                    self._checkpoint(state, "dns_snapshot", dns_snapshot)
                    scores = asyncio.run(self.dns.benchmark(dns_snapshot.get("ServerAddresses", [])))
                    winner = self.dns.select_best(scores)
                    if winner:
                        state["dns_changed"] = True
                        state["dns_provider"] = winner.name
                        self.state_store.save(state)
                        self.dns.apply(interface.index, winner)
                    report["network"]["dns"] = {
                        "changed": bool(winner),
                        "selected": winner.name if winner else "Current",
                        "benchmarks": [score.to_dict() for score in scores],
                    }
                except Exception as exc:
                    state["warnings"].append(f"DNS optimization skipped: {exc}")
                    self.state_store.save(state)

            if not interface.probably_virtual:
                try:
                    mtu_result = self.mtu.recommend(interface.mtu)
                    report["network"]["mtu"] = mtu_result
                    if mtu_result.get("apply"):
                        self._checkpoint(state, "mtu_snapshot", {"interface_index": interface.index, "mtu": interface.mtu})
                        state["mtu_changed"] = True
                        self.state_store.save(state)
                        self.mtu.apply(interface.index, int(mtu_result["recommended"]))
                except Exception as exc:
                    state["warnings"].append(f"MTU auto-tuning skipped: {exc}")
                    self.state_store.save(state)

        # Never firewall-steer Riot or CS2. For other titles, the existing
        # verified/interchangeable-pool guard remains mandatory.
        if protected or hardcore or not network_requested:
            report["network"]["smart_route"] = {
                "skipped": True,
                "reason": "Safe Core: endpoint blocking/firewall steering disabled",
            }
        elif interface is not None and interface.probably_virtual:
            report["network"]["smart_route"] = {"skipped": True, "reason": "VPN/virtual interface detected"}
        else:
            try:
                definition = self.catalog.get(game["id"])
                route_reports = []
                for pool in definition.pools:
                    if not pool.endpoints:
                        continue
                    stats = asyncio.run(probe_many(pool.endpoints))
                    decision = self.route_policy.decide(pool, stats, strict=profile is BoostProfile.AGGRESSIVE)
                    route_reports.append({
                        "pool": pool.id,
                        "measurements": [s.to_dict() for s in stats],
                        "decision": decision.to_dict(),
                    })
                    if decision.blocked_endpoints:
                        rules = self.firewall.prepare(
                            game["id"], pool.id, str(game["executable"]), [e.ip for e in decision.blocked_endpoints]
                        )
                        for rule in rules:
                            state["firewall_rules"].append(rule["name"])
                            self.state_store.save(state)
                            self.firewall.apply(rule)
                report["network"]["smart_route"] = route_reports
            except Exception as exc:
                state["warnings"].append(f"Endpoint steering skipped: {exc}")
                self.state_store.save(state)

        # Protected games: no priority, affinity, CPU Sets or process handle
        # manipulation. Ordinary/Roblox profiles retain process optimization.
        if not process_mutations:
            report["hardware"]["process"] = {
                "skipped": True,
                "reason": "Safe Core: game process left untouched",
            }
        else:
            try:
                proc_snapshot = ProcessOptimizer.snapshot(int(game["pid"]))
                self._checkpoint(state, "process_snapshot", proc_snapshot)
                proc_snapshot = ProcessOptimizer.apply(proc_snapshot, aggressive=profile is BoostProfile.AGGRESSIVE)
                self._checkpoint(state, "process_snapshot", proc_snapshot)
                report["hardware"]["process"] = {
                    "priority": "high" if profile is BoostProfile.AGGRESSIVE else "above-normal",
                    "p_core_sets": proc_snapshot.get("applied_cpu_sets", []),
                }
            except Exception as exc:
                state["warnings"].append(f"Process optimization skipped: {exc}")
                self.state_store.save(state)

        # Temporary cloned system power plan. This is outside the game process
        # and restored on STOP/crash recovery.
        try:
            if not power_plan_allowed:
                raise RuntimeError("mode does not permit power-plan mutation")
            original_power = self.power.active_guid()
            self._checkpoint(state, "power_snapshot", {"changed": True, "original": original_power, "temporary": None})
            power_snapshot = self.power.apply(aggressive=profile is BoostProfile.AGGRESSIVE, original=original_power)
            self._checkpoint(state, "power_snapshot", power_snapshot)
            report["hardware"]["power"] = power_snapshot
        except Exception as exc:
            state["warnings"].append(f"Power plan optimization skipped: {exc}")
            self.state_store.save(state)

        report["hardware"]["nvidia"] = nvidia_telemetry()

        # Aggressive-only experimental mutations can never be reached from a
        # protected-game profile due to effective_profile's hard downgrade.
        if profile is BoostProfile.AGGRESSIVE:
            try:
                tcp = TcpTweaks(interface.guid)
                tcp_snapshot = tcp.snapshot()
                self._checkpoint(state, "tcp_snapshot", tcp_snapshot)
                tcp.apply()
                report["network"]["experimental_tcp"] = True
            except Exception as exc:
                state["warnings"].append(f"Experimental TCP tweaks skipped: {exc}")
                self.state_store.save(state)
            try:
                report["hardware"]["standby_purge"] = purge_standby_list()
            except Exception as exc:
                state["warnings"].append(f"Standby purge skipped: {exc}")
            try:
                svc_snapshot = self.services.snapshot()
                self._checkpoint(state, "services_snapshot", svc_snapshot)
                self.services.pause(svc_snapshot)
                self._checkpoint(state, "services_snapshot", svc_snapshot)
                report["hardware"]["paused_services"] = [x.get("Name") for x in svc_snapshot if x.get("PausedByNexus")]
                report["hardware"]["service_skips"] = [
                    {"name": x.get("Name"), "reason": x.get("SkipReason") or x.get("PauseError")}
                    for x in svc_snapshot
                    if not x.get("PausedByNexus") and (x.get("SkipReason") or x.get("PauseError"))
                ]
            except Exception as exc:
                state["warnings"].append(f"Service pause skipped: {exc}")
                self.state_store.save(state)

        state["report"] = report
        self.state_store.save(state)
        return report

    def capture_quality_after(self) -> dict | None:
        state = self.state_store.load()
        if not state.get("active"):
            return None
        after = self.quality_store.snapshot(25.0)
        state["quality_after"] = after
        try:
            state["gaming_health_after"] = gaming_health(protected_runtime=self._state_is_protected(state))
        except Exception as exc:
            state.setdefault("warnings", []).append(f"Gaming health after snapshot skipped: {exc}")
        self.state_store.save(state)
        return after

    def adaptive_reassess(self) -> dict | None:
        """Re-evaluate a degraded live session without disruptive mutations.

        DNS, route and endpoint candidates are recalculated, but no live game
        sockets, firewall rules, process state or resolver are changed. The
        recommendation can be used on the next connection/session.
        """
        state = self.state_store.load()
        if not state.get("active"):
            return None
        game = state.get("game") or {}
        protected_session = self._state_is_protected(state)
        quality = self.quality_store.snapshot(20.0)
        event: dict = {
            "timestamp": time.time(),
            "quality": quality,
            "action": "read_only_reassessment",
            "applied_live_changes": False,
            "reason": "Adaptive Booster avoids disruptive in-session network changes.",
        }

        try:
            if protected_session:
                # No PowerShell/interface lookup while Vanguard/VAC title is live.
                scores = asyncio.run(self.dns.benchmark([]))
                public_winner = min(
                    (score for score in scores if score.median_ms is not None and score.success_rate >= 0.75),
                    key=lambda score: score.score,
                    default=None,
                )
                event["dns"] = {
                    "diagnostic_only": True,
                    "current_resolver_queried": False,
                    "recommended_public_resolver_for_next_session": public_winner.provider.name if public_winner else None,
                    "benchmarks": [score.to_dict() for score in scores],
                }
            else:
                interface = InterfaceManager.primary_ipv4()
                if not interface.probably_virtual and interface.network_category != "DomainAuthenticated":
                    dns_snapshot = self.dns.snapshot(interface.index, interface.guid)
                    scores = asyncio.run(self.dns.benchmark(dns_snapshot.get("ServerAddresses", [])))
                    winner = self.dns.select_best(scores)
                    event["dns"] = {
                        "recommended_for_next_connection": winner.name if winner else "Current",
                        "benchmarks": [score.to_dict() for score in scores],
                    }
        except Exception as exc:
            event["dns_error"] = str(exc)

        # Re-evaluate verified endpoint pools for non-protected games, but do
        # not firewall-block anything while a live session exists.
        if not protected_session:
            try:
                definition = self.catalog.get(str(game.get("id")))
                recommendations = []
                for pool in definition.pools:
                    if not pool.endpoints or not pool.interchangeable:
                        continue
                    stats = asyncio.run(probe_many(pool.endpoints, attempts=3))
                    decision = self.route_policy.decide(pool, stats, strict=False)
                    recommendations.append({
                        "pool": pool.id,
                        "best_endpoint": decision.best_endpoint.ip if decision.best_endpoint else None,
                        "measurements": [s.to_dict() for s in stats],
                    })
                event["endpoint_recommendations"] = recommendations
            except Exception as exc:
                event["endpoint_error"] = str(exc)

        # Route diagnostic is read-only and is never used as an automatic
        # firewall/routing decision by itself.
        target = quality.get("target") or "1.1.1.1"
        try:
            event["route"] = trace_route(str(target), max_hops=16, probes_per_hop=2, timeout_ms=500)
        except Exception as exc:
            event["route_error"] = str(exc)

        state.setdefault("adaptive_events", []).append(event)
        state["adaptive_events"] = state["adaptive_events"][-20:]
        self.state_store.save(state)
        return event

    def restore_all(self) -> dict:
        state = self.state_store.load()
        if not state.get("active"):
            return {"restored": False, "message": "No active NexuFlow snapshot"}
        errors: list[str] = []

        # Capture the final quality/health picture before rollback so session
        # history can show a genuine before/after comparison.
        try:
            if not state.get("quality_after"):
                state["quality_after"] = self.quality_store.snapshot(25.0)
            state["gaming_health_after"] = gaming_health(protected_runtime=self._state_is_protected(state))
            self.state_store.save(state)
        except Exception as exc:
            state.setdefault("warnings", []).append(f"Final session metrics skipped: {exc}")
            self.state_store.save(state)

        for name in state.get("firewall_rules", []):
            try:
                self.firewall.delete(name)
            except Exception as exc:
                errors.append(f"firewall {name}: {exc}")

        if state.get("dns_changed") and state.get("dns_snapshot"):
            try:
                self.dns.restore(state["dns_snapshot"])
            except Exception as exc:
                errors.append(f"dns: {exc}")

        if state.get("mtu_changed") and state.get("mtu_snapshot"):
            try:
                self.mtu.restore(int(state["mtu_snapshot"]["interface_index"]), int(state["mtu_snapshot"]["mtu"]))
            except Exception as exc:
                errors.append(f"mtu: {exc}")

        if state.get("tcp_snapshot") is not None:
            try:
                TcpTweaks.restore(state["tcp_snapshot"])
            except Exception as exc:
                errors.append(f"tcp: {exc}")

        if state.get("process_snapshot"):
            try:
                ProcessOptimizer.restore(state["process_snapshot"])
            except Exception as exc:
                errors.append(f"process: {exc}")

        if state.get("power_snapshot"):
            try:
                self.power.restore(state["power_snapshot"])
            except Exception as exc:
                errors.append(f"power: {exc}")

        if state.get("services_snapshot"):
            try:
                self.services.restore(state["services_snapshot"])
            except Exception as exc:
                errors.append(f"services: {exc}")

        state["ended_at"] = time.time()
        state["restore_errors"] = errors
        history_error = None
        try:
            history_record = self.history.record_state(state, ended_at=state["ended_at"])
        except Exception as exc:
            history_record = None
            # Session history is useful but non-critical. A history I/O error
            # must never keep a fully restored system marked as dirty.
            history_error = str(exc)

        if errors:
            state["restore_errors"] = errors
            state["restore_attempted_at"] = time.time()
            if history_error:
                state.setdefault("warnings", []).append(f"history: {history_error}")
            self.state_store.save(state)
        else:
            self.state_store.clear()
        return {
            "restored": not errors,
            "errors": errors,
            "history": history_record,
            "history_error": history_error,
            "message": "NexuFlow changes restored" if not errors else "Rollback completed with warnings; snapshot preserved for retry",
        }
