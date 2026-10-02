#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_root"
image_tag="${IMAGE:-liaogui-shixun:release-20261001}"
bundle="artifacts/release/liaogui-offline-amd64-20261001"
mkdir -p "$bundle"
if [[ "${SKIP_BUILD:-0}" == 1 ]]; then
  [[ -n "${VERIFIED_IMAGE_ID:-}" ]] || { echo 'SKIP_BUILD requires VERIFIED_IMAGE_ID' >&2; exit 1; }
  [[ "$(docker image inspect --format '{{.Id}}' "$image_tag")" == "$VERIFIED_IMAGE_ID" ]] || { echo 'Verified image ID mismatch' >&2; exit 1; }
else
  docker build --platform linux/amd64 -f Dockerfile.offline -t "$image_tag" .
fi
cp deploy/offline/* "$bundle/"
printf '%s\n' "$image_tag" > "$bundle/IMAGE"
mkdir -p "$bundle/docs"
find docs/release -maxdepth 1 -type f -exec cp {} "$bundle/docs/" \;
docker image inspect "$image_tag" > "$bundle/image-inspect.json"
docker run --rm --network none --entrypoint pip "$image_tag" freeze > "$bundle/python-packages.txt"
git rev-parse HEAD > "$bundle/SOURCE_COMMIT"
docker save "$image_tag" | gzip -1 > "$bundle/image.tar.gz"
python3 - "$bundle" <<'PY'
import hashlib,pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
(root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root))+'\n' for p in files))
with zipfile.ZipFile(str(root)+'.zip','w',compression=zipfile.ZIP_STORED) as archive:
    for p in sorted(root.rglob('*')):
        if p.is_file():archive.write(p,p.relative_to(root.parent))
print(str(root)+'.zip')
PY
