$ErrorActionPreference = "Stop"

function Invoke-Python {
    param([string[]]$PythonArgs)

    $candidates = @()
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
                & $exe @prefix @PythonArgs
                exit $LASTEXITCODE
            }
        } catch {
            continue
        }
    }
    throw "No working Python interpreter found"
}

Invoke-Python @("-c", "import sys; sys.path.insert(0, 'src'); from app.plugins.manifest_loader import load_all_plugin_manifests; manifests=load_all_plugin_manifests(); print('PLUGIN_COUNT', len(manifests)); print([(m.id, m.activation, m.threaded_background) for m in manifests])")
