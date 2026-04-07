#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/host-tests"
BIN_PATH="${BUILD_DIR}/host-tests"

mkdir -p "${BUILD_DIR}"

c++ \
  -std=c++17 \
  -Wall \
  -Wextra \
  -Werror \
  "${ROOT_DIR}/tests/host/test_main.cpp" \
  "${ROOT_DIR}/tests/host/test_access_logic.cpp" \
  "${ROOT_DIR}/tests/host/test_config_model.cpp" \
  "${ROOT_DIR}/tests/host/test_runtime_guards.cpp" \
  "${ROOT_DIR}/src/core/AccessLogic.cpp" \
  "${ROOT_DIR}/src/core/ConfigModel.cpp" \
  "${ROOT_DIR}/src/core/RuntimeGuards.cpp" \
  -o "${BIN_PATH}"

"${BIN_PATH}"
