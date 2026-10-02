#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
check_docker
[[ $# == 2 ]] || { echo '用法：restore.sh /完整路径/backup.enc /新的空恢复目录' >&2; exit 1; }
backup_path="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
mkdir -p "$2"
restore_path="$(cd -- "$2" && pwd)"
[[ -z "$(ls -A "$restore_path")" ]] || { echo '拒绝覆盖非空目录。' >&2; exit 1; }
docker run --rm --network none --user 0 --env-file "$ENV_FILE" --entrypoint python \
  -v "$backup_path:/restore.enc:ro" -v "$restore_path:/restored" "$IMAGE" -c 'import os,json;from app.services.operations_runtime import restore_to_new_directory;print(json.dumps(restore_to_new_directory("/restore.enc","/restored",os.environ["BACKUP_ENCRYPTION_KEY"])));[(os.chown(os.path.join(root,name),10001,10001)) for root,dirs,files in os.walk("/restored") for name in dirs+files];os.chown("/restored",10001,10001)'
echo "恢复与校验完成，尚未切换运行数据。切换时先 stop.sh，再 DATA_DIR='$restore_path' start.sh。保留原目录供回退。"
