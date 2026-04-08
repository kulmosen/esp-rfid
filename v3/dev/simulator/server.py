#!/usr/bin/env python3
"""Minimal ESP-RFID V3 door simulator."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulatorState:
    """Shared mutable simulator state."""

    def __init__(self) -> None:
        self.device_id = os.getenv("SIM_DEVICE_ID", "frontdoor")
        self.door_name = os.getenv("SIM_DOOR_NAME", "Front Door")
        self.api_token = os.getenv("SIM_API_TOKEN", "dev-token")
        self.allow_hold_open = _env_bool("SIM_ALLOW_HOLD_OPEN", True)
        self.snapshot_version = os.getenv("SIM_SNAPSHOT_VERSION", "demo-v1")
        self.firmware_version = os.getenv("SIM_FIRMWARE_VERSION", "v3-simulator")
        self.default_pulse_ms = int(os.getenv("SIM_PULSE_MS", "1500"))
        self.lock_state = "locked"
        self.health_state = "online"
        self.event_queue_depth = 0
        self.credential_count = 0
        self.snapshot_generated_at: str | None = None
        self.last_sync_at = _utc_now()
        self.relay_active = False
        self.last_error: str | None = None
        self.last_command: str | None = None
        self.boot_count = 1
        self.last_snapshot_payload: dict[str, Any] | None = None
        self._pulse_timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        """Return public device status."""
        with self._lock:
            return {
                "device_id": self.device_id,
                "door_name": self.door_name,
                "health_state": self.health_state,
                "lock_state": self.lock_state,
                "snapshot_version": self.snapshot_version,
                "event_queue_depth": self.event_queue_depth,
                "credential_count": self.credential_count,
                "snapshot_generated_at": self.snapshot_generated_at,
                "last_sync_at": self.last_sync_at,
                "firmware_version": self.firmware_version,
                "relay_active": self.relay_active,
                "hold_supported": self.allow_hold_open,
                "last_error": self.last_error,
                "last_command": self.last_command,
                "boot_count": self.boot_count,
            }

    def _clear_pulse_timer(self) -> None:
        if self._pulse_timer is not None:
            self._pulse_timer.cancel()
            self._pulse_timer = None

    def _set_locked(self) -> None:
        with self._lock:
            self.lock_state = "locked"
            self.relay_active = False
            self.last_error = None
            self.last_command = "auto_lock"
            self._pulse_timer = None

    def pulse_unlock(self, reason: str) -> None:
        with self._lock:
            self._clear_pulse_timer()
            self.lock_state = "pulse_active"
            self.relay_active = True
            self.last_command = f"pulse_unlock:{reason}"
            self.last_error = None
            self.event_queue_depth += 1
            self._pulse_timer = threading.Timer(self.default_pulse_ms / 1000.0, self._set_locked)
            self._pulse_timer.daemon = True
            self._pulse_timer.start()

    def hold_unlock(self, reason: str) -> bool:
        with self._lock:
            if not self.allow_hold_open:
                self.last_error = "hold_unlock_not_supported"
                return False

            self._clear_pulse_timer()
            self.lock_state = "hold_active"
            self.relay_active = True
            self.last_command = f"hold_unlock:{reason}"
            self.last_error = None
            self.event_queue_depth += 1
            return True

    def cancel_hold(self, reason: str) -> None:
        with self._lock:
            self._clear_pulse_timer()
            self.lock_state = "locked"
            self.relay_active = False
            self.last_command = f"cancel_hold:{reason}"
            self.last_error = None
            self.event_queue_depth += 1

    def resync(self) -> None:
        with self._lock:
            self.last_sync_at = _utc_now()
            self.last_command = "resync"
            self.last_error = None
            self.event_queue_depth = 0
            self.snapshot_version = f"{self.snapshot_version.split('+', 1)[0]}+{int(time.time())}"

    def reboot(self) -> None:
        with self._lock:
            self.boot_count += 1
            self.last_command = "reboot"
            self.last_error = None
            self.health_state = "online"
            self.lock_state = "locked"
            self.relay_active = False
            self.event_queue_depth = 0

    def apply_snapshot(self, payload: dict[str, Any]) -> bool:
        """Apply a pushed snapshot payload."""
        with self._lock:
            if payload.get("device_id") != self.device_id:
                self.last_error = "snapshot_device_mismatch"
                return False

            users = payload.get("users")
            if not isinstance(users, list):
                self.last_error = "snapshot_users_invalid"
                return False

            self.snapshot_version = str(payload.get("version", self.snapshot_version))
            self.snapshot_generated_at = str(
                payload.get("generated_at", self.snapshot_generated_at or _utc_now())
            )
            self.credential_count = len(users)
            self.last_snapshot_payload = payload
            self.last_sync_at = _utc_now()
            self.last_command = "apply_snapshot"
            self.last_error = None
            return True


STATE = SimulatorState()


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler."""

    server_version = "EspRfidV3Simulator/0.1"

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def _is_authorized(self) -> bool:
        expected = f"Bearer {STATE.api_token}"
        return self.headers.get("Authorization") == expected

    def _require_auth(self) -> bool:
        if self._is_authorized():
            return True
        self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/v1/status":
            if not self._require_auth():
                return
            self._write_json(HTTPStatus.OK, STATE.snapshot())
            return

        if parsed.path == "/api/debug/state":
            self._write_json(HTTPStatus.OK, STATE.snapshot())
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path.startswith("/v1/command/"):
            if not self._require_auth():
                return

            command = parsed.path.rsplit("/", 1)[-1]
            payload = self._read_json()
            reason = str(payload.get("reason", "unspecified"))

            if command == "pulse_unlock":
                STATE.pulse_unlock(reason)
                self._write_json(HTTPStatus.ACCEPTED, {"ok": True, "command": command})
                return

            if command == "hold_unlock":
                if not STATE.hold_unlock(reason):
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "hold_unlock_not_supported"},
                    )
                    return
                self._write_json(HTTPStatus.ACCEPTED, {"ok": True, "command": command})
                return

            if command == "cancel_hold":
                STATE.cancel_hold(reason)
                self._write_json(HTTPStatus.ACCEPTED, {"ok": True, "command": command})
                return

            if command == "resync":
                STATE.resync()
                self._write_json(HTTPStatus.ACCEPTED, {"ok": True, "command": command})
                return

            if command == "reboot":
                STATE.reboot()
                self._write_json(HTTPStatus.ACCEPTED, {"ok": True, "command": command})
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "unknown_command"})
            return

        if parsed.path == "/v1/snapshot":
            if not self._require_auth():
                return

            payload = self._read_json()
            if not STATE.apply_snapshot(payload):
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"ok": False, "error": STATE.last_error or "snapshot_rejected"},
                )
                return

            self._write_json(
                HTTPStatus.ACCEPTED,
                {
                    "ok": True,
                    "snapshot_version": STATE.snapshot_version,
                    "credential_count": STATE.credential_count,
                },
            )
            return

        if parsed.path == "/api/debug/reset":
            STATE.cancel_hold("debug_reset")
            STATE.event_queue_depth = 0
            STATE.last_sync_at = _utc_now()
            STATE.last_command = "debug_reset"
            STATE.credential_count = 0
            STATE.snapshot_generated_at = None
            STATE.last_snapshot_payload = None
            self._write_json(HTTPStatus.OK, {"ok": True})
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        """Keep simulator output compact."""
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")


def main() -> None:
    """Run the simulator."""
    bind_host = os.getenv("SIM_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("SIM_PORT", "18101"))
    server = ThreadingHTTPServer((bind_host, port), Handler)
    print(
        f"ESP-RFID V3 simulator listening on http://{bind_host}:{port} "
        f"for {STATE.device_id} ({STATE.door_name})"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
