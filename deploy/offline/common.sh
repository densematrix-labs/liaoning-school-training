#!/usr/bin/env bash
set -euo pipefail
BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$BUNDLE_DIR/site}"
CONTAINER_NAME="${CONTAINER_NAME:-liaogui-training}"
IMAGE="${IMAGE:-$(cat "$BUNDLE_DIR/IMAGE") }"
IMAGE="${IMAGE% }"
DATA_DIR="${DATA_DIR:-$INSTALL_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
ENV_FILE="$INSTALL_DIR/site.env"
check_docker() {
  command -v docker >/dev/null || { echo 'Docker Engine 未安装。请使用与 Ubuntu 版本匹配的离线安装介质；此包不在线下载软件。' >&2; exit 1; }
  docker info >/dev/null 2>&1 || { echo 'Docker 未运行或当前用户没有 Docker 权限。' >&2; exit 1; }
}
