#!/usr/bin/env python3
"""Upload a firmware bundle or binary to an ESP-RFID device."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import pathlib
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any


def build_basic_auth_header(username: str, password: str) -> str:
    token = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(token).decode("ascii")


def normalize_base_url(host: str, port: int, scheme: str) -> str:
    if "://" in host:
        return host.rstrip("/")
    default_port = 443 if scheme == "https" else 80
    if port == default_port:
        return f"{scheme}://{host}".rstrip("/")
    return f"{scheme}://{host}:{port}".rstrip("/")


def login_check(base_url: str, username: str, password: str, timeout: int) -> str:
    request = urllib.request.Request(
        f"{base_url}/login",
        headers={
            "Authorization": build_basic_auth_header(username, password),
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace").strip()


def encode_multipart_formdata(field_name: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"esp-rfid-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(data)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary


def upload_firmware(
    base_url: str,
    username: str,
    password: str,
    firmware_path: pathlib.Path,
    timeout: int,
) -> str:
    payload = firmware_path.read_bytes()
    body, boundary = encode_multipart_formdata("update", firmware_path.name, payload)

    request = urllib.request.Request(
        f"{base_url}/update",
        data=body,
        headers={
            "Authorization": build_basic_auth_header(username, password),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace").strip()


def resolve_bundle_firmware(bundle_dir: pathlib.Path) -> pathlib.Path:
    manifest_path = bundle_dir / "manifest.json"
    if manifest_path.exists():
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        firmware_name = manifest["artifacts"]["firmware"]["filename"]
        firmware_path = bundle_dir / firmware_name
        if not firmware_path.exists():
            raise FileNotFoundError(f"Bundle manifest points to missing firmware: {firmware_path}")
        return firmware_path

    binaries = sorted(bundle_dir.glob("*.bin"))
    if len(binaries) != 1:
        raise FileNotFoundError(
            f"Could not resolve a single firmware binary in {bundle_dir}. "
            f"Expected one .bin file or a manifest.json."
        )
    return binaries[0]


def resolve_firmware_path(args: argparse.Namespace) -> pathlib.Path:
    if args.bundle:
        bundle_dir = pathlib.Path(args.bundle).expanduser().resolve()
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")
        return resolve_bundle_firmware(bundle_dir)

    if args.firmware:
        firmware_path = pathlib.Path(args.firmware).expanduser().resolve()
        if not firmware_path.exists():
            raise FileNotFoundError(f"Firmware file not found: {firmware_path}")
        return firmware_path

    raise FileNotFoundError("Provide either --bundle or --firmware")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Device IP, hostname, or full base URL")
    parser.add_argument("--port", type=int, default=80, help="HTTP port when --host is not a full URL")
    parser.add_argument("--scheme", default="http", choices=["http", "https"], help="URL scheme")
    parser.add_argument("--username", default="admin", help="HTTP basic auth username")
    parser.add_argument("--password", required=True, help="HTTP basic auth password")
    parser.add_argument("--bundle", default="", help="Path to a bundle directory created by release_bundle.py")
    parser.add_argument("--firmware", default="", help="Path to a firmware binary")
    parser.add_argument("--timeout", type=int, default=60, help="Network timeout in seconds")
    parser.add_argument("--skip-login-check", action="store_true", help="Upload directly without checking /login first")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        firmware_path = resolve_firmware_path(args)
        base_url = normalize_base_url(args.host, args.port, args.scheme)

        print(f"[ INFO ] Target   : {base_url}")
        print(f"[ INFO ] Firmware : {firmware_path}")

        if not args.skip_login_check:
            login_response = login_check(base_url, args.username, args.password, args.timeout)
            print(f"[ INFO ] Login OK : {login_response or 'Success'}")

        upload_response = upload_firmware(
            base_url=base_url,
            username=args.username,
            password=args.password,
            firmware_path=firmware_path,
            timeout=args.timeout,
        )
        print(f"[ OK ] Upload response: {upload_response or '<empty response>'}")
        return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"[ ERRO ] HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"[ ERRO ] Network error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - shell script style entrypoint
        print(f"[ ERRO ] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
