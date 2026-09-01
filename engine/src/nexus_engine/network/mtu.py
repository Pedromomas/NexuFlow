from __future__ import annotations

from .icmp import icmp_echo_ipv4
from ..anti_cheat import assert_mutation_allowed
from ..policy_runtime import assert_feature_enabled
from ..winexec import powershell_json, run_command


class MTUManager:
    TARGETS = ("1.1.1.1", "8.8.8.8", "9.9.9.9")

    @staticmethod
    def _works(ip: str, payload: int, attempts: int = 2) -> bool:
        success = 0
        for _ in range(attempts):
            latency, status = icmp_echo_ipv4(ip, 650, payload, True)
            if latency is not None and status == 0:
                success += 1
        return success == attempts

    def _max_payload(self, ip: str) -> int | None:
        # Never infer PMTU from a target that cannot reliably echo a
        # conservative DF packet. This intentionally prefers "no change" over
        # a false low MTU caused by filtered ICMP.
        if not self._works(ip, 1200, 2):
            return None
        lo, hi, best = 1200, 1472, 1200
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._works(ip, mid, 1):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best if self._works(ip, best, 2) else None

    def recommend(self, current_mtu: int) -> dict:
        current_mtu = int(current_mtu)
        # Respect unusual user/network configurations. NexuFlow only auto-tunes
        # the normal Internet Ethernet range and never normalizes jumbo/custom
        # adapters behind the user's back.
        if not 1280 <= current_mtu <= 1500:
            return {
                "apply": False,
                "current": current_mtu,
                "recommended": current_mtu,
                "reason": "Custom/jumbo MTU detected; automatic tuning skipped",
                "samples": [],
            }

        payloads = [p for p in (self._max_payload(ip) for ip in self.TARGETS) if p is not None]
        if len(payloads) < 2:
            return {
                "apply": False,
                "current": current_mtu,
                "recommended": current_mtu,
                "reason": "Insufficient reliable DF/ICMP targets",
                "samples": payloads,
            }
        if max(payloads) - min(payloads) > 24:
            return {
                "apply": False,
                "current": current_mtu,
                "recommended": current_mtu,
                "reason": "PMTU targets disagree",
                "samples": payloads,
            }

        proposed = min(payloads) + 28  # IPv4 + ICMP headers
        if proposed < 1280:
            return {
                "apply": False,
                "current": current_mtu,
                "recommended": current_mtu,
                "reason": "Measured PMTU is below the automatic safety floor",
                "samples": payloads,
            }
        proposed = min(1500, proposed)
        should_apply = proposed <= current_mtu - 8
        return {
            "apply": should_apply,
            "current": current_mtu,
            "recommended": proposed if should_apply else current_mtu,
            "reason": "Consensus PMTU reduction" if should_apply else "Current MTU is already appropriate",
            "samples": payloads,
        }

    @staticmethod
    def apply(interface_index: int, mtu: int) -> None:
        assert_mutation_allowed("mtu_mutation")
        assert_feature_enabled("mtu_apply")
        mtu = int(mtu)
        if not 1280 <= mtu <= 1500:
            raise ValueError("Refusing unsafe automatic MTU value")
        powershell_json(
            rf"Set-NetIPInterface -InterfaceIndex {int(interface_index)} -AddressFamily IPv4 -NlMtuBytes {mtu} -ErrorAction Stop; @{{ok=$true}} | ConvertTo-Json -Compress"
        )

    @staticmethod
    def restore(interface_index: int, mtu: int) -> None:
        # Rollback must accept the user's original custom value, including
        # jumbo frames. This path uses only a previously snapshotted value.
        mtu = int(mtu)
        if not 576 <= mtu <= 65535:
            raise ValueError("Invalid snapshotted MTU value")
        run_command([
            "netsh", "interface", "ipv4", "set", "subinterface",
            str(int(interface_index)), f"mtu={mtu}", "store=persistent",
        ])
