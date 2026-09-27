#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PERF_PYTHON:-python3}"

if ! "${PYTHON_BIN}" -c 'import httpx' >/dev/null 2>&1; then
  echo "缺少 httpx。请先执行：python3 -m pip install -r backend/requirements.txt" >&2
  exit 2
fi

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" scripts/performance_demo.py "$@"
