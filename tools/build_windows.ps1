$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv run python -m PyInstaller tools\suishou.spec --noconfirm
