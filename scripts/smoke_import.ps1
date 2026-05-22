$ErrorActionPreference = "Stop"

function Invoke-Python {
    param([string[]]$PythonArgs)

    $candidates = @()
    if ($env:SUISHOU_PYTHON) {
        $candidates += [pscustomobject]@{ Exe = $env:SUISHOU_PYTHON; Prefix = @() }
    }
    if ($env:PY_DESKTOP_TOOLS_PYTHON) {
        $candidates += [pscustomobject]@{ Exe = $env:PY_DESKTOP_TOOLS_PYTHON; Prefix = @() }
    }
    if (Test-Path ".\.venv\Scripts\python.exe") {
        $candidates += [pscustomobject]@{ Exe = ".\.venv\Scripts\python.exe"; Prefix = @() }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += [pscustomobject]@{ Exe = "py"; Prefix = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidates += [pscustomobject]@{ Exe = "python"; Prefix = @() }
    }
    $codexPython = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $codexPython) {
        $candidates += [pscustomobject]@{ Exe = $codexPython; Prefix = @() }
    }

    foreach ($candidate in $candidates) {
        $exe = $candidate.Exe
        $prefix = $candidate.Prefix
        try {
            & $exe @prefix -c "print('PYTHON_OK')" *> $null
            if ($LASTEXITCODE -eq 0) {
                & $exe @prefix -c "import PySide6" *> $null
                if ($LASTEXITCODE -ne 0) {
                    continue
                }
                & $exe @prefix @PythonArgs
                exit $LASTEXITCODE
            }
        } catch {
            continue
        }
    }
    throw "No working Python interpreter found"
}

Invoke-Python @("-c", "import sys; sys.path.insert(0, 'src'); import app.main; print('IMPORT_APP_MAIN_OK')")
