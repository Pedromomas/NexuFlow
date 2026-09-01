from __future__ import annotations

import os

from ..anti_cheat import assert_mutation_allowed
from ..policy_runtime import assert_feature_enabled


class TcpTweaks:
    """Aggressive-only, reversible Windows registry network tweaks.

    The snapshot path is read-only: it never creates Registry keys while
    observing the current configuration. Restore reinstates the original value
    and type, or removes only the value NexuFlow created.
    """

    def __init__(self, interface_guid: str):
        self.interface_guid = interface_guid if interface_guid.startswith("{") else "{" + interface_guid + "}"

    def _targets(self) -> list[tuple[str, str, int]]:
        return [
            (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 0xFFFFFFFF),
            (rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{self.interface_guid}", "TcpAckFrequency", 1),
            (rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{self.interface_guid}", "TCPNoDelay", 1),
        ]

    def snapshot(self) -> list[dict]:
        if os.name != "nt":
            return []
        import winreg

        result: list[dict] = []
        for path, name, _ in self._targets():
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ) as key:
                    try:
                        old, typ = winreg.QueryValueEx(key, name)
                        result.append({
                            "path": path,
                            "name": name,
                            "key_existed": True,
                            "existed": True,
                            "value": old,
                            "type": typ,
                        })
                    except FileNotFoundError:
                        result.append({"path": path, "name": name, "key_existed": True, "existed": False})
            except FileNotFoundError:
                result.append({"path": path, "name": name, "key_existed": False, "existed": False})
        return result

    def apply(self) -> None:
        assert_mutation_allowed("tcp_registry_tweaks")
        assert_feature_enabled("tcp_tweaks")
        if os.name != "nt":
            return
        import winreg

        for path, name, value in self._targets():
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))

    @staticmethod
    def restore(snapshot: list[dict]) -> None:
        if os.name != "nt":
            return
        import winreg

        errors: list[str] = []
        for item in snapshot:
            path = str(item["path"])
            name = str(item["name"])
            try:
                # The target key normally exists for real interfaces/SystemProfile.
                # CreateKeyEx is used only during rollback when needed to restore a
                # value that existed in the original snapshot.
                if item.get("existed"):
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.SetValueEx(key, name, 0, int(item["type"]), item.get("value"))
                else:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as key:
                            try:
                                winreg.DeleteValue(key, name)
                            except FileNotFoundError:
                                pass
                    except FileNotFoundError:
                        pass
            except OSError as exc:
                errors.append(f"{path}::{name}: {exc}")
        if errors:
            raise RuntimeError("Registry rollback failed: " + "; ".join(errors))
