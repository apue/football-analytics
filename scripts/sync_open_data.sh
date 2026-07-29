#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${FOOTBALL_ANALYTICS_DATA_ROOT:-${PROJECT_ROOT}/data/external}"
OPEN_DATA_ROOT="${DATA_ROOT}/statsbomb-open-data"
OPEN_DATA_URL="${FOOTBALL_ANALYTICS_OPEN_DATA_URL:-https://github.com/hudl/open-data.git}"

mkdir -p "${DATA_ROOT}"

if [[ -d "${OPEN_DATA_ROOT}/.git" ]]; then
  git -C "${OPEN_DATA_ROOT}" rev-parse --verify HEAD >/dev/null
  git -C "${OPEN_DATA_ROOT}" pull --ff-only
elif [[ -e "${OPEN_DATA_ROOT}" ]]; then
  echo "Refusing to replace non-Git path: ${OPEN_DATA_ROOT}" >&2
  exit 1
else
  CLONE_ROOT="$(mktemp -d "${DATA_ROOT}/.open-data-clone.XXXXXX")"
  cleanup() {
    rm -rf "${CLONE_ROOT}"
  }
  trap cleanup EXIT

  git clone \
    --depth 1 \
    --filter=blob:none \
    --sparse \
    "${OPEN_DATA_URL}" \
    "${CLONE_ROOT}/repository"
  git -C "${CLONE_ROOT}/repository" sparse-checkout set \
    --no-cone \
    /README.md \
    /LICENSE.pdf \
    /data/competitions.json
  mv "${CLONE_ROOT}/repository" "${OPEN_DATA_ROOT}"
  trap - EXIT
  rmdir "${CLONE_ROOT}"
fi

git -C "${OPEN_DATA_ROOT}" rev-parse HEAD
