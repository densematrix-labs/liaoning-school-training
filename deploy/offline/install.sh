#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
"$BUNDLE_DIR/preflight.sh"
docker load -i "$BUNDLE_DIR/image.tar.gz" >/dev/null
mkdir -p "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR"
if [[ ! -e "$ENV_FILE" ]]; then
  umask 077
  docker run --rm --network none --entrypoint python "$IMAGE" -c 'import secrets;from cryptography.fernet import Fernet;print("DEPLOYMENT_MODE=pilot\nRELEASE_MODE=true\nDEBUG=false\nSECRET_KEY="+secrets.token_urlsafe(48)+"\nBOOTSTRAP_ADMIN_USER=admin\nBOOTSTRAP_ADMIN_PASSWORD="+secrets.token_urlsafe(24)+"\nBACKUP_ENCRYPTION_KEY="+Fernet.generate_key().decode()+"\nAUDIT_RETENTION_DAYS=180\nBACKUP_RETENTION_DAYS=30")' > "$ENV_FILE"
  cat "$BUNDLE_DIR/site.env.example" >> "$ENV_FILE"
fi
mkdir -p "$DATA_DIR" "$BACKUP_DIR"
docker run --rm --network none --user 0 --entrypoint python -v "$DATA_DIR:/target-data" -v "$BACKUP_DIR:/target-backups" "$IMAGE" -c 'import os;[(os.chown(p,10001,10001),os.chmod(p,0o700)) for p in ("/target-data","/target-backups")]'
"$BUNDLE_DIR/start.sh"
echo "安装完成。初始密码与备份密钥仅保存在 $ENV_FILE；请私下交给管理员并独立保管密钥。"
