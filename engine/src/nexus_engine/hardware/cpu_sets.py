from __future__ import annotations

import ctypes
import os
import struct
from ctypes import wintypes

from ..anti_cheat import assert_mutation_allowed

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_LIMITED_INFORMATION = 0x2000


def system_cpu_sets() -> list[dict]:
    if os.name != "nt":
        return []
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = kernel32.GetSystemCpuSetInformation
    fn.argtypes = [ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG), wintypes.HANDLE, wintypes.ULONG]
    fn.restype = wintypes.BOOL
    needed = wintypes.ULONG(0)
    fn(None, 0, ctypes.byref(needed), None, 0)
    if not needed.value:
        return []
    buf = ctypes.create_string_buffer(needed.value)
    if not fn(buf, needed.value, ctypes.byref(needed), None, 0):
        return []
    result, offset = [], 0
    while offset + 8 <= needed.value:
        size, typ = struct.unpack_from("<II", buf.raw, offset)
        if size < 8 or offset + size > needed.value:
            break
        if typ == 0 and size >= 32:  # CpuSetInformation
            _, _, cpu_id, group, logical, core, llc, numa, efficiency, flags, scheduling, tag = struct.unpack_from("<IIIHBBBBBBIQ", buf.raw, offset)
            result.append({
                "id": cpu_id, "group": group, "logical": logical, "core": core,
                "llc": llc, "numa": numa, "efficiency_class": efficiency,
                "parked": bool(flags & 1), "allocated": bool(flags & 2),
                "scheduling_class": scheduling & 0xFF, "allocation_tag": tag,
            })
        offset += size
    return result


def _open_process(pid: int):
    assert_mutation_allowed("cpu_sets", pid=int(pid))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_LIMITED_INFORMATION, False, int(pid))
    return kernel32, handle


def get_process_cpu_sets(pid: int) -> list[int]:
    assert_mutation_allowed("cpu_sets", pid=int(pid))
    if os.name != "nt":
        return []
    kernel32, handle = _open_process(pid)
    if not handle:
        return []
    try:
        needed = wintypes.ULONG(0)
        fn = kernel32.GetProcessDefaultCpuSets
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG), wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
        fn.restype = wintypes.BOOL
        fn(handle, None, 0, ctypes.byref(needed))
        if needed.value == 0:
            return []
        arr = (wintypes.ULONG * needed.value)()
        if not fn(handle, arr, needed.value, ctypes.byref(needed)):
            return []
        return [int(x) for x in arr[:needed.value]]
    finally:
        kernel32.CloseHandle(handle)


def set_process_cpu_sets(pid: int, ids: list[int]) -> bool:
    assert_mutation_allowed("cpu_sets", pid=int(pid))
    if os.name != "nt":
        return False
    kernel32, handle = _open_process(pid)
    if not handle:
        return False
    try:
        fn = kernel32.SetProcessDefaultCpuSets
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG), wintypes.ULONG]
        fn.restype = wintypes.BOOL
        if not ids:
            return bool(fn(handle, None, 0))
        arr = (wintypes.ULONG * len(ids))(*ids)
        return bool(fn(handle, arr, len(ids)))
    finally:
        kernel32.CloseHandle(handle)


def preferred_performance_sets() -> list[int]:
    sets = [x for x in system_cpu_sets() if not x["parked"]]
    if not sets:
        return []
    classes = {x["efficiency_class"] for x in sets}
    if len(classes) < 2:
        return []  # Homogeneous CPU: let Windows schedule normally.
    best_class = max(classes)  # Microsoft: higher EfficiencyClass = faster, less power-efficient.
    return [int(x["id"]) for x in sets if x["efficiency_class"] == best_class]
