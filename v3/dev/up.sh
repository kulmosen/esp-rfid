#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
SOURCE_DIR="$SCRIPT_DIR/../home_assistant/custom_components/esp_rfid_v3"
TARGET_ROOT="$SCRIPT_DIR/homeassistant/custom_components"
TARGET_DIR="$TARGET_ROOT/esp_rfid_v3"

mkdir -p "$TARGET_ROOT"

if command -v rsync >/dev/null 2>&1; then
  mkdir -p "$TARGET_DIR"
  rsync -a --delete "$SOURCE_DIR/" "$TARGET_DIR/"
else
  rm -rf "$TARGET_DIR"
  cp -R "$SOURCE_DIR" "$TARGET_DIR"
fi

exec docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d "$@"
