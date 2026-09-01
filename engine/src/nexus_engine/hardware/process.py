from __future__ import annotations

import os

import psutil

from ..anti_cheat import assert_mutation_allowed, protected_pid_game
from ..policy_runtime import assert_feature_enabled, feature_enabled
from .cpu_sets import get_process_cpu_sets, preferred_performance_sets, set_process_cpu_sets


class ProcessOptimizer:
    @staticmethod
    def snapshot(pid: int) -> dict:
        # Guard before constructing psutil.Process so protected games never get
        # an optimization/query handle opened by this module.
        assert_mutation_allowed("process_optimization", pid=int(pid))
        proc = psutil.Process(int(pid))
        return {
            "pid": int(pid),
            "create_time": float(proc.create_time()),
            "priority": proc.nice(),
            "cpu_sets": get_process_cpu_sets(pid),
            "cpu_sets_changed": False,
        }

    @staticmethod
    def apply(snapshot: dict, aggressive: bool = False) -> dict:
        pid = int(snapshot["pid"])
        assert_mutation_allowed("process_optimization", pid=pid)
        assert_feature_enabled("process_priority")
        proc = psutil.Process(pid)
        expected = float(snapshot.get("create_time", proc.create_time()))
        if abs(proc.create_time() - expected) > 1.0:
            raise RuntimeError("Game PID was reused before optimization could be applied")

        if os.name == "nt":
            target = psutil.HIGH_PRIORITY_CLASS if aggressive else psutil.ABOVE_NORMAL_PRIORITY_CLASS
            proc.nice(target)
            preferred = preferred_performance_sets() if feature_enabled("cpu_sets") else []
            if preferred:
                if not set_process_cpu_sets(pid, preferred):
                    raise RuntimeError("Windows rejected the requested performance CPU Sets")
                snapshot["cpu_sets_changed"] = True
                snapshot["applied_cpu_sets"] = preferred
        return snapshot

    @staticmethod
    def restore(snapshot: dict) -> dict:
        pid = int(snapshot.get("pid", 0))
        if not pid or not psutil.pid_exists(pid):
            return {"restored": False, "reason": "process exited"}

        # Legacy snapshots may predate the protected-game policy. Never open a
        # currently protected process merely to roll back process-local state;
        # Windows discards priority/CPU-set state when that process exits.
        protected = protected_pid_game(pid)
        if protected:
            return {
                "restored": False,
                "reason": f"protected process left untouched: {protected}",
                "safe_to_forget_after_process_exit": True,
            }

        try:
            proc = psutil.Process(pid)
            expected = float(snapshot.get("create_time", 0.0))
            # Never modify an unrelated process that inherited the same PID.
            if expected and abs(proc.create_time() - expected) > 1.0:
                return {"restored": False, "reason": "pid reused"}
            proc.nice(snapshot.get("priority", proc.nice()))
            if snapshot.get("cpu_sets_changed"):
                original = [int(x) for x in snapshot.get("cpu_sets", [])]
                if not set_process_cpu_sets(pid, original):
                    raise RuntimeError("Windows rejected CPU Set rollback")
            return {"restored": True}
        except psutil.NoSuchProcess:
            return {"restored": False, "reason": "process exited"}
        except (psutil.AccessDenied, OSError, ValueError) as exc:
            raise RuntimeError(f"Process rollback failed for PID {pid}: {exc}") from exc
