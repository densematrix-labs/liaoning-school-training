#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
check_docker
architecture="$(docker info --format '{{.Architecture}}')"
case "$architecture" in x86_64|amd64) ;; *) echo "当前包仅支持 linux/amd64；Docker 主机为 $architecture。请获取对应架构镜像。" >&2; exit 1;; esac
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  [[ "${ID:-}" == ubuntu && "${VERSION_ID%%.*}" -ge 20 ]] || { echo '此包的交付目标为 Ubuntu 20+；当前系统需另行验证。' >&2; exit 1; }
fi
[[ -r "$BUNDLE_DIR/SHA256SUMS" ]] && (cd "$BUNDLE_DIR" && sha256sum -c SHA256SUMS)
echo '预检通过：Docker 可用，架构匹配。建议至少 4 核 / 8GB 内存 / 40GB 可用空间；实际容量取决于图片与备份。'
echo '仍需校方确认：数据盘空间、域名/HTTPS、网络与数据库只读权限。'
