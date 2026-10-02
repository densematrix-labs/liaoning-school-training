#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
check_docker
[[ -f "$ENV_FILE" ]] || { echo '请先执行 install.sh' >&2; exit 1; }
# Do not source site.env: it is data, not shell code.
if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  echo "容器 $CONTAINER_NAME 已存在。配置变更或升级请先 stop.sh；不会自动删除现有容器。" >&2; exit 1
fi
docker run -d --name "$CONTAINER_NAME" --restart unless-stopped --pull never \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,noexec,size=256m \
  --log-driver json-file --log-opt max-size=20m --log-opt max-file=5 \
  --env-file "$ENV_FILE" -v "$DATA_DIR:/data" -v "$BACKUP_DIR:/backups" \
  -p "${BIND_ADDRESS:-127.0.0.1}:${PORT:-8080}:8080" "$IMAGE" >/dev/null
for attempt in $(seq 1 60); do
  if docker exec "$CONTAINER_NAME" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)" >/dev/null 2>&1; then
    echo "服务正常：http://${BIND_ADDRESS:-127.0.0.1}:${PORT:-8080}"
    exit 0
  fi
  sleep 2
done
echo '启动健康检查失败。保留容器与数据，请执行 docker logs 查看错误。' >&2
exit 1
