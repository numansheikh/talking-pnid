#!/usr/bin/env bash
# package_for_training.sh
# ─────────────────────────────────────────────────────────────────────────────
# Packages everything needed to train on the Linux/3090 machine.
# Resolves symlinks so the tar is self-contained.
#
# Output: pid_training_package.tar.gz  (~same size as actual image data)
#
# Usage (on Mac):
#   bash scripts/package_for_training.sh
#
# Then on Linux:
#   tar -xzf pid_training_package.tar.gz
#   cd model-pretrain
#   pip install ultralytics
#   python scripts/step7_train.py
# ─────────────────────────────────────────────────────────────────────────────

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
PACKAGE_DIR="${ROOT}/pid_training_package"
OUT_TAR="${ROOT}/../pid_training_package.tar.gz"

echo "==> Building self-contained training package ..."
echo "    Source: ${ROOT}"
echo "    Output: ${OUT_TAR}"

rm -rf "${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}/model-pretrain"

DST="${PACKAGE_DIR}/model-pretrain"

# ── Scripts & config ─────────────────────────────────────────────────────────
echo "    Copying scripts and config ..."
cp -r "${ROOT}/scripts"       "${DST}/scripts"
cp -r "${ROOT}/config"        "${DST}/config"
cp -r "${ROOT}/datasets/class_names.yaml" "${DST}/"

# ── Dataset (resolve all symlinks → real files) ───────────────────────────────
echo "    Copying augmented dataset (resolving symlinks) ..."
echo "    This may take a few minutes for 161k images ..."

for split in train val test; do
  mkdir -p "${DST}/datasets/augmented/images/${split}"
  mkdir -p "${DST}/datasets/augmented/labels/${split}"

  echo "      images/${split} ..."
  # cp -L follows symlinks
  cp -L "${ROOT}/datasets/augmented/images/${split}/"* \
        "${DST}/datasets/augmented/images/${split}/" 2>/dev/null || true

  echo "      labels/${split} ..."
  cp    "${ROOT}/datasets/augmented/labels/${split}/"* \
        "${DST}/datasets/augmented/labels/${split}/" 2>/dev/null || true
done

# Copy dataset.yaml with corrected absolute path (will be fixed on Linux side)
cp "${ROOT}/datasets/augmented/dataset.yaml" "${DST}/datasets/augmented/dataset.yaml"

# ── Fix dataset.yaml path (make it relative-friendly) ────────────────────────
python3 -c "
import yaml
from pathlib import Path
dst = Path('${DST}/datasets/augmented/dataset.yaml')
with open(dst) as f:
    cfg = yaml.safe_load(f)
# Use placeholder — setup_linux.sh will replace with actual path
cfg['path'] = '__REPLACE_WITH_ABSOLUTE_PATH__'
with open(dst, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
"

# ── Setup script for Linux ────────────────────────────────────────────────────
cat > "${DST}/setup_linux.sh" << 'EOF'
#!/usr/bin/env bash
# Run this once on the Linux machine after extracting the package.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up training environment on Linux ..."

# Fix dataset.yaml path
python3 -c "
import yaml, sys
from pathlib import Path
cfg_path = Path('${ROOT}/datasets/augmented/dataset.yaml')
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)
cfg['path'] = str(Path('${ROOT}/datasets/augmented').resolve())
with open(cfg_path, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('dataset.yaml path updated to:', cfg['path'])
"

# Install dependencies
pip install ultralytics albumentations -q

echo ""
echo "Setup complete. To start training:"
echo "  cd ${ROOT}"
echo "  python scripts/step7_train.py"
EOF
chmod +x "${DST}/setup_linux.sh"

# ── Create tarball ────────────────────────────────────────────────────────────
echo ""
echo "==> Creating tarball (this will take a while) ..."
tar -czf "${OUT_TAR}" -C "${PACKAGE_DIR}" model-pretrain

SIZE=$(du -sh "${OUT_TAR}" | cut -f1)
echo ""
echo "==> Done!"
echo "    Package: ${OUT_TAR}  (${SIZE})"
echo ""
echo "Transfer to Linux:"
echo "  rsync -avz --progress ${OUT_TAR} user@linux-machine:~/"
echo ""
echo "On Linux:"
echo "  tar -xzf ~/pid_training_package.tar.gz -C ~/"
echo "  cd ~/model-pretrain"
echo "  bash setup_linux.sh"
echo "  python scripts/step7_train.py"
