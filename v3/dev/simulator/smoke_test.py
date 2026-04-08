#!/usr/bin/env python3
"""Smoke test for the local ESP-RFID V3 simulator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"


def http_json(url: str, method: str = "GET", token: str | None = None, payload: dict | None = None) -> dict:
    """Perform a JSON request."""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_status(url: str, token: str) -> None:
    """Wait for the simulator to become available."""
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            http_json(url, token=token)
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Simulator did not become ready in time")


def main() -> int:
    """Run the smoke test."""
    env = os.environ.copy()
    env.setdefault("SIM_BIND_HOST", "127.0.0.1")
    env.setdefault("SIM_PORT", "19101")
    env.setdefault("SIM_DEVICE_ID", "smoke-door")
    env.setdefault("SIM_DOOR_NAME", "Smoke Door")
    env.setdefault("SIM_API_TOKEN", "smoke-token")
    env.setdefault("SIM_SNAPSHOT_VERSION", "smoke-v1")

    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(SERVER)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{env['SIM_PORT']}"
    status_url = f"{base_url}/v1/status"

    try:
        wait_for_status(status_url, env["SIM_API_TOKEN"])

        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["lock_state"] == "locked"
        assert status["device_id"] == "smoke-door"
        assert status["credential_count"] == 0

        http_json(
            f"{base_url}/v1/command/pulse_unlock",
            method="POST",
            token=env["SIM_API_TOKEN"],
            payload={"reason": "smoke"},
        )
        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["lock_state"] == "pulse_active"

        http_json(
            f"{base_url}/v1/command/hold_unlock",
            method="POST",
            token=env["SIM_API_TOKEN"],
            payload={"reason": "smoke"},
        )
        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["lock_state"] == "hold_active"

        http_json(
            f"{base_url}/v1/command/cancel_hold",
            method="POST",
            token=env["SIM_API_TOKEN"],
            payload={"reason": "smoke"},
        )
        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["lock_state"] == "locked"

        previous_snapshot = status["snapshot_version"]
        http_json(
            f"{base_url}/v1/command/resync",
            method="POST",
            token=env["SIM_API_TOKEN"],
            payload={},
        )
        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["snapshot_version"] != previous_snapshot

        snapshot_payload = {
            "site_name": "Smoke Site",
            "device_id": "smoke-door",
            "door_name": "Smoke Door",
            "generated_at": "2026-04-08T12:00:00+00:00",
            "version": "smoke-snapshot-v2",
            "allow_hold_open": True,
            "users": [
                {
                    "user_id": "dennis",
                    "name": "Dennis",
                    "tag_digest": "abc123",
                    "pin_hash": None,
                    "pin_salt": None,
                    "pin_iterations": None,
                    "valid_from": None,
                    "valid_until": None,
                }
            ],
        }
        http_json(
            f"{base_url}/v1/snapshot",
            method="POST",
            token=env["SIM_API_TOKEN"],
            payload=snapshot_payload,
        )
        status = http_json(status_url, token=env["SIM_API_TOKEN"])
        assert status["snapshot_version"] == "smoke-snapshot-v2"
        assert status["credential_count"] == 1
        assert status["snapshot_generated_at"] == "2026-04-08T12:00:00+00:00"

        try:
            http_json(status_url)
            raise AssertionError("Unauthorized request unexpectedly succeeded")
        except urllib.error.HTTPError as err:
            assert err.code == 401

        print("ESP-RFID V3 simulator smoke test passed")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
        if process.stdout is not None:
            output = process.stdout.read().strip()
            if output:
                print(output)


if __name__ == "__main__":
    raise SystemExit(main())
