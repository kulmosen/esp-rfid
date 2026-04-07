# AGENTS.md

## Purpose

This repository contains the `esp-rfid` firmware for ESP8266-based access control devices with support for MFRC522, PN532, Wiegand, and RDM6300 readers. The codebase mixes firmware, generated web assets, helper tools, and release/build scripts.

Use this file as the first stop before making changes. The project is buildable, but parts of the codebase are old and fragile, so changes should prioritize stability and backwards compatibility over sweeping rewrites.

## Repository Map

- `src/main.cpp`
  - Main firmware translation unit.
  - Pulls in most of the application through `#include "*.esp"` files.
  - Defines the global objects and state used across the project.
- `src/*.esp`
  - Feature modules included into `main.cpp`.
  - These are not standalone compilation units.
  - Important modules:
    - `config.esp`: loads `/config.json`, initializes hardware/network settings.
    - `wifi.esp`: AP/STA/fallback WiFi logic.
    - `mqtt.esp`: MQTT connection, publishing, and command handling.
    - `websocket.esp`: WebSocket message queue and command dispatch.
    - `webserver.esp`: HTTP routes and OTA update endpoint.
    - `rfid.esp`: card reading, PIN flow, access processing.
    - `log.esp`: SPIFFS/MQTT event logging.
- `src/websrc/`
  - Editable web UI source files.
  - Third-party frontend libraries are vendored here.
- `src/webh/`
  - Generated gzipped header files embedded in firmware.
  - Do not edit manually.
- `tools/webfilesbuilder/`
  - Rebuilds the generated web asset headers from `src/websrc/`.
- `tools/wsemulator/`
  - Local WebSocket emulator for UI development.
- `scripts/*.py`
  - PlatformIO post-build scripts copying firmware images into `bin/`.
- `.github/workflows/`
  - CI for firmware and helper tools.

## Core Architecture Notes

- The firmware is heavily stateful and relies on globals declared in `src/main.cpp`.
- Persistence is SPIFFS-based:
  - `/config.json` stores device configuration.
  - `/P/<uid>` stores user records.
  - `/eventlog.json` and `/latestlog.json` store logs.
- The UI talks to the firmware through WebSocket JSON commands.
- OTA upload is exposed through `/update` and uses HTTP basic auth.
- MQTT is optional but tightly integrated with boot, access events, and remote commands.
- Reader support is selected from config and initialized during startup in `loadConfiguration()`.

## Build And Local Commands

### Firmware

- Build release firmware:
  - `platformio run -e generic`
- Build debug firmware:
  - `platformio run -e debug`
- Output binaries are copied to:
  - `bin/generic.bin`
  - `bin/debug.bin`

### Web UI

- Rebuild generated web headers after changing anything in `src/websrc/`:
  - `cd tools/webfilesbuilder`
  - `npm install`
  - `npm start`
- This regenerates `src/webh/*.gz.h`.

### UI Emulation

- Run the WebSocket emulator:
  - `cd tools/wsemulator`
  - `npm install`
  - `node wserver.js`

## Working Rules For Agents

- Treat `src/webh/*` as generated artifacts. Edit `src/websrc/*` instead, then regenerate.
- When changing config handling, keep old config files readable. The repository already expects config backwards compatibility.
- When touching firmware logic, remember that `.esp` files are compiled by inclusion into `main.cpp`; symbol collisions and hidden cross-module coupling are common.
- Be conservative with flash and heap usage. ESP8266 is still memory-constrained even if the current build fits comfortably.
- Avoid introducing more dynamic allocation unless there is a strong reason.
- Prefer incremental refactors over broad rewrites. This codebase has many hidden runtime assumptions.
- If you touch logging, file layout, or auth flows, think about migration and recovery on already deployed devices.

## Generated And Vendored Files

- Generated:
  - `src/webh/*.gz.h`
- Vendored frontend dependencies:
  - `src/websrc/3rdparty/js/01-jquery-1.12.4.min.js`
  - `src/websrc/3rdparty/js/02-bootstrap-3.3.7.min.js`
  - `src/websrc/3rdparty/js/03-footable-3.1.6.min.js`
  - `src/websrc/3rdparty/css/*.min.css`

Do not hand-edit minified third-party assets unless the task is specifically to upgrade them.

## Stability Priorities

### 1. Lock Down The Toolchain

- `platformio.ini` still pins an old ESP8266 platform (`espressif8266@2.3.2`) and uses partially ambiguous dependency specs.
- Before larger feature work, pin all libraries with explicit owners/versions and verify CI still resolves the same packages every time.
- Keep toolchain updates separate from functional refactors.

### 2. Reduce Heap Fragmentation

- The firmware uses many global `String`s, `strdup`, `malloc`, and manual queues.
- ESP8266 heap fragmentation is a realistic long-term stability risk.
- Focus especially on:
  - WebSocket message handling
  - MQTT message handling
  - config parsing and string ownership
  - repeated log/message serialization paths

### 3. Harden WiFi/MQTT Recovery

- WiFi reconnect behavior is delicate and should be validated carefully after any changes.
- MQTT reconnect, availability publishing, and remote command processing should be tested under AP mode, STA mode, and intermittent network loss.

### 4. Plan A SPIFFS Migration

- The project still uses SPIFFS everywhere.
- For long-term maintainability, plan a controlled migration to LittleFS or another supported storage option.
- Do this only with a clear migration/backwards-compatibility plan, because user/config storage is central to deployed devices.

### 5. Add Real Verification

- There are builds in CI, but effectively no automated behavioral tests.
- High-value additions would be:
  - config parsing tests
  - access decision tests
  - MQTT command tests
  - host-side tests around user file parsing and migration logic

## Known Hotspots

### `src/wifi.esp`

- WiFi event handling is brittle.
- `connectSTA()` is blocking and uses polling delays.
- Reconnect and fallback behavior should be treated as a regression-sensitive area.

### `src/websocket.esp`

- Manual queueing and ownership management are easy to break.
- Be careful with allocation/free semantics and fragmented WebSocket frames.

### `src/mqtt.esp`

- MQTT commands are parsed into a custom linked list queue.
- There is little bounds validation for relay indexes and command payload assumptions.
- Connection recovery and message safety should be improved before adding new MQTT features.

### `src/config.esp`

- Config loading mixes parsing, allocation, validation, and hardware setup in one function.
- This file is a good candidate for staged cleanup:
  - schema validation
  - normalization/defaulting
  - application of config to subsystems

### `src/log.esp`

- Logging is append-only and SPIFFS-backed.
- Any changes here must consider flash wear, large-file behavior, and log maintenance commands.

### `src/rfid.esp`

- The state machine is workable but spread across globals and side effects.
- Access control, PIN processing, reader-specific logic, messaging, and cleanup are tightly coupled.

## Recommended Refactor Order

1. Fix obvious correctness issues in WiFi/MQTT/WebSocket memory management.
2. Pin and modernize dependency declarations in `platformio.ini`.
3. Extract config parsing/validation from hardware side effects.
4. Add host-side tests for access decisions and config compatibility.
5. Reduce `String` churn in the hottest runtime paths.
6. Only then consider larger platform upgrades such as newer ESP8266 core or filesystem migration.

## Review Checklist For Changes

- Does it preserve existing `/config.json` compatibility?
- Does it preserve existing `/P/<uid>` user file behavior?
- If web UI files changed, were `src/webh/*.gz.h` regenerated?
- Does the firmware still build for both `generic` and `debug`?
- Does the change increase heap churn, blocking time, or filesystem writes?
- Does it behave sensibly in both AP mode and STA mode?
- If MQTT was touched, did command handling and reconnect behavior get re-tested?

## Branching And Contribution Context

- The repository documentation says:
  - bug fixes target `stable`
  - new features target `dev`
- If you are working locally without opening a PR, still keep this convention in mind when describing or preparing changes.

## Suggested Near-Term Work

- Fix runtime correctness issues before feature work.
- Add a small host-side test harness for config and access logic.
- Replace ambiguous dependency specs with explicit pinned packages.
- Start shrinking dynamic allocation in the networking and messaging paths.
