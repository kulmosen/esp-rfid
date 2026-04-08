#!/usr/bin/env python3
"""Create versioned firmware bundles that can be reused for rollback."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "releases"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "release"


def detect_platformio_command() -> list[str]:
    if shutil.which("platformio"):
        return ["platformio"]
    return [sys.executable, "-m", "platformio"]


def run_command(command: list[str], cwd: pathlib.Path = REPO_ROOT) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def run_git_command(args: list[str], default: str) -> str:
    try:
        completed = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return default
    return completed.stdout.strip() or default


def git_metadata() -> dict[str, Any]:
    dirty = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=str(REPO_ROOT),
        check=False,
    ).returncode != 0

    staged_dirty = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(REPO_ROOT),
        check=False,
    ).returncode != 0

    return {
        "branch": run_git_command(["branch", "--show-current"], "unknown"),
        "commit": run_git_command(["rev-parse", "HEAD"], "unknown"),
        "short_commit": run_git_command(["rev-parse", "--short", "HEAD"], "unknown"),
        "dirty": dirty or staged_dirty,
    }


def sha256_for_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_firmware(env_name: str) -> pathlib.Path:
    command = detect_platformio_command() + ["run", "-e", env_name]
    run_command(command)
    firmware_path = REPO_ROOT / ".pio" / "build" / env_name / "firmware.bin"
    if not firmware_path.exists():
        raise FileNotFoundError(f"Firmware not found after build: {firmware_path}")
    return firmware_path


def resolve_firmware_path(args: argparse.Namespace) -> pathlib.Path:
    if args.firmware:
        firmware_path = pathlib.Path(args.firmware).expanduser().resolve()
        if not firmware_path.exists():
            raise FileNotFoundError(f"Firmware file not found: {firmware_path}")
        return firmware_path

    if not args.skip_build:
        return build_firmware(args.env)

    firmware_path = REPO_ROOT / ".pio" / "build" / args.env / "firmware.bin"
    if not firmware_path.exists():
        raise FileNotFoundError(
            f"Firmware not found at {firmware_path}. Run a build first or omit --skip-build."
        )
    return firmware_path


def build_manifest(
    args: argparse.Namespace,
    bundle_dir: pathlib.Path,
    bundle_name: str,
    bundle_filename: str,
    firmware_source: pathlib.Path,
    firmware_sha256: str,
) -> dict[str, Any]:
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    git = git_metadata()
    firmware_size = firmware_source.stat().st_size

    return {
        "schema": 1,
        "bundle_name": bundle_name,
        "label": args.label,
        "device_label": args.device_label,
        "environment": args.env,
        "created_at": created_at.isoformat(),
        "git": git,
        "artifacts": {
            "firmware": {
                "filename": bundle_filename,
                "size_bytes": firmware_size,
                "sha256": firmware_sha256,
                "source_path": str(firmware_source),
            }
        },
        "paths": {
            "bundle_dir": str(bundle_dir),
        },
        "notes": [
            "Take a settings backup and a user backup from the web UI before updating a live door.",
            "Use tools/device_update.py with this bundle to install or roll back this firmware.",
            "Firmware rollback does not restore SPIFFS content automatically; keep the exported backups with the bundle.",
        ],
    }


def render_readme(manifest: dict[str, Any]) -> str:
    firmware = manifest["artifacts"]["firmware"]
    bundle_dir = manifest["paths"]["bundle_dir"]
    return f"""# Rollback Kit

This bundle was created for cautious firmware rollouts.

## What is inside

* Firmware: `{firmware["filename"]}`
* SHA256: `{firmware["sha256"]}`
* Source commit: `{manifest["git"]["commit"]}`
* Environment: `{manifest["environment"]}`
* Device label: `{manifest["device_label"] or "unspecified"}`

## Recommended rollout flow

1. Open the device web UI and export:
   * `Backup Settings`
   * `Backup User Data`
2. Keep those JSON backups together with this bundle.
3. Install the candidate firmware on the less critical door first.
4. If the device behaves badly, roll back by installing this bundle again.

## Upload this bundle

```sh
python3 tools/device_update.py --host <device-ip-or-hostname> --password <admin-password> --bundle "{bundle_dir}"
```

## Important note

Rolling back firmware does not roll back settings, users, or logs. That data lives in SPIFFS, so always keep the exported JSON backups next to the bundle when testing a live door.
"""


def create_bundle(args: argparse.Namespace) -> pathlib.Path:
    firmware_source = resolve_firmware_path(args)

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_name = f"{timestamp}-{slugify(args.label)}"
    bundle_dir = pathlib.Path(args.output_root).expanduser().resolve() / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=False)

    bundle_filename = f"{slugify(args.env)}-firmware.bin"
    bundled_firmware = bundle_dir / bundle_filename
    shutil.copy2(firmware_source, bundled_firmware)

    firmware_sha256 = sha256_for_file(bundled_firmware)
    manifest = build_manifest(
        args=args,
        bundle_dir=bundle_dir,
        bundle_name=bundle_name,
        bundle_filename=bundle_filename,
        firmware_source=firmware_source,
        firmware_sha256=firmware_sha256,
    )

    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + os.linesep,
        encoding="utf-8",
    )
    (bundle_dir / "SHA256SUMS.txt").write_text(
        f"{firmware_sha256}  {bundle_filename}{os.linesep}",
        encoding="utf-8",
    )
    (bundle_dir / "ROLLBACK.md").write_text(
        render_readme(manifest),
        encoding="utf-8",
    )

    print(f"[ OK ] Created firmware bundle: {bundle_dir}")
    print(f"[ INFO ] Firmware: {bundle_filename}")
    print(f"[ INFO ] SHA256 : {firmware_sha256}")
    return bundle_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Build and package a firmware bundle")
    create.add_argument("--label", required=True, help="Human-readable label, for example backdoor-baseline")
    create.add_argument("--env", default="generic", help="PlatformIO environment to build")
    create.add_argument(
        "--device-label",
        default="",
        help="Optional target label such as backdoor or frontdoor",
    )
    create.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where bundles will be created",
    )
    create.add_argument(
        "--firmware",
        default="",
        help="Use an existing firmware binary instead of building one",
    )
    create.add_argument(
        "--skip-build",
        action="store_true",
        help="Do not run PlatformIO; use the existing .pio/build/<env>/firmware.bin",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "create":
            create_bundle(args)
            return 0
    except Exception as exc:  # pragma: no cover - shell script style entrypoint
        print(f"[ ERRO ] {exc}", file=sys.stderr)
        return 1

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
