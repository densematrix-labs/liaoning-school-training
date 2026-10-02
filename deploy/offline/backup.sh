#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
check_docker
docker exec "$CONTAINER_NAME" python -c 'import json;from app.services.operations_runtime import backup_database;print(json.dumps(backup_database(),ensure_ascii=False))'
