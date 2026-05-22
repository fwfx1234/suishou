#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group build
uv run python -m PyInstaller tools/suishou.spec --noconfirm
