#!/usr/bin/env bash
# Download a local whisper.cpp CLI + tiny.en model. No API key.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${ROOT}/tools/whisper"
mkdir -p "${DEST}"

VERSION="${WHISPER_CPP_VERSION:-v1.8.7}"
ARCHIVE="whisper-bin-ubuntu-x64.tar.gz"
URL="https://github.com/ggml-org/whisper.cpp/releases/download/${VERSION}/${ARCHIVE}"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"

echo "Installing whisper.cpp ${VERSION} into ${DEST}"
curl -fsSL "${URL}" -o "${DEST}/${ARCHIVE}"
tar -xzf "${DEST}/${ARCHIVE}" -C "${DEST}"

# Release tarballs vary: find whisper-cli or main.
BIN=""
for candidate in \
  "${DEST}/whisper-cli" \
  "${DEST}/build/bin/whisper-cli" \
  "${DEST}/bin/whisper-cli" \
  "${DEST}/main"
do
  if [[ -f "${candidate}" ]]; then
    BIN="${candidate}"
    break
  fi
done
if [[ -z "${BIN}" ]]; then
  BIN="$(find "${DEST}" -type f -name 'whisper-cli' -o -name 'main' | head -n 1 || true)"
fi
if [[ -z "${BIN}" ]]; then
  echo "Could not find whisper-cli in the release archive" >&2
  exit 1
fi
chmod +x "${BIN}"
ln -sfn "${BIN}" "${DEST}/whisper-cli"

if [[ ! -f "${DEST}/ggml-tiny.en.bin" ]]; then
  echo "Downloading ggml-tiny.en.bin"
  curl -fL "${MODEL_URL}" -o "${DEST}/ggml-tiny.en.bin"
fi

echo "WHISPER_BIN=${DEST}/whisper-cli"
echo "WHISPER_MODEL=${DEST}/ggml-tiny.en.bin"
"${DEST}/whisper-cli" -h >/dev/null 2>&1 || true
echo "Done. The scan CLI will pick these up automatically."
