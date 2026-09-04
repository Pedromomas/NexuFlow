from __future__ import annotations

import http.client
import statistics
import time
from typing import Callable

from ..anti_cheat import running_protected_games
from ..daemon import daemon_is_running
from .connection_center import _scan_lock
from .allowlist import BOUNDED_TRANSFER_HOSTS


SPEED_TEST_HOST = "speed.cloudflare.com"
DOWNLOAD_SIZES = (8 * 1024 * 1024, 16 * 1024 * 1024)
UPLOAD_SIZES = (2 * 1024 * 1024, 4 * 1024 * 1024)
MAX_TRANSFER_BYTES = sum(DOWNLOAD_SIZES) + sum(UPLOAD_SIZES)


def _download(size: int, now: Callable[[], float] = time.perf_counter) -> float:
    connection = http.client.HTTPSConnection(SPEED_TEST_HOST, 443, timeout=18)
    started = now()
    received = 0
    try:
        connection.request("GET", f"/__down?bytes={size}", headers={"Cache-Control": "no-store", "User-Agent": "NexuFlow/2.1-beta"})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"speed endpoint returned HTTP {response.status}")
        while True:
            chunk = response.read(min(256 * 1024, size - received if received < size else 256 * 1024))
            if not chunk:
                break
            received += len(chunk)
            if received > size:
                raise RuntimeError("speed endpoint exceeded the bounded response size")
    finally:
        connection.close()
    elapsed = max(now() - started, 0.001)
    if received < size:
        raise RuntimeError("speed endpoint returned an incomplete download")
    return (received * 8) / elapsed / 1_000_000


def _upload(size: int, now: Callable[[], float] = time.perf_counter) -> float:
    connection = http.client.HTTPSConnection(SPEED_TEST_HOST, 443, timeout=18)
    payload = bytes(size)
    started = now()
    try:
        connection.request(
            "POST",
            f"/__up?bytes={size}",
            body=payload,
            headers={"Content-Type": "application/octet-stream", "Cache-Control": "no-store", "User-Agent": "NexuFlow/2.1-beta"},
        )
        response = connection.getresponse()
        response.read(64 * 1024)
        if response.status not in (200, 204):
            raise RuntimeError(f"speed endpoint returned HTTP {response.status}")
    finally:
        connection.close()
    elapsed = max(now() - started, 0.001)
    return (size * 8) / elapsed / 1_000_000


def run_speed_test() -> dict:
    """Run a bounded, user-triggered throughput sample against one fixed host.

    This is deliberately not automatic: the test transfers up to 30 MiB and the
    remote provider necessarily observes the public source IP. No result is sent
    back by NexuFlow and no system/network setting is changed.
    """
    if SPEED_TEST_HOST not in BOUNDED_TRANSFER_HOSTS:
        raise RuntimeError("Speed test endpoint is not allowlisted.")
    if running_protected_games():
        raise RuntimeError("Feche a partida protegida antes do teste de velocidade.")
    if daemon_is_running():
        raise RuntimeError("Desative o BOOST antes do teste para não disputar banda com uma sessão de jogo.")
    with _scan_lock():
        started = time.time()
        downloads = [_download(size) for size in DOWNLOAD_SIZES]
        uploads = [_upload(size) for size in UPLOAD_SIZES]
        return {
            "schema": 1,
            "kind": "bounded_speed_test",
            "measured_at": started,
            "provider": "Cloudflare speed test edge",
            "endpoint": SPEED_TEST_HOST,
            "download_mbps": round(statistics.median(downloads), 1),
            "upload_mbps": round(statistics.median(uploads), 1),
            "download_samples_mbps": [round(value, 1) for value in downloads],
            "upload_samples_mbps": [round(value, 1) for value in uploads],
            "transferred_bytes_max": MAX_TRANSFER_BYTES,
            "read_only": True,
            "mutation_performed": False,
            "note": (
                "Amostra rápida e aproximada para um único edge. O provedor recebe o IP público necessário à conexão; "
                "o NexuFlow não envia o resultado e não altera DNS, rota ou adaptador."
            ),
        }
