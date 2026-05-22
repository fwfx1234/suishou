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
                & $exe @prefix @PythonArgs
                exit $LASTEXITCODE
            }
        } catch {
            continue
        }
    }
    throw "No working Python interpreter found"
}

Invoke-Python @("-c", "import os, sys, sqlite3, shutil; from pathlib import Path; root=Path.cwd() / '.tmp' / 'suishou_storage_smoke'; shutil.rmtree(root, ignore_errors=True); os.environ['SUISHOU_DATA_DIR']=str(root); sys.path.insert(0, 'src'); from app.storage import StorageManager; s=StorageManager(); st=s.dict_store('smoke/settings', defaults={'enabled': True}); st['limit']=3; print(st.get('enabled'), st.get('limit'), st.path.name, st.namespace); conn=sqlite3.connect(st.path); print(conn.execute('select namespace,key,value_json from dict_store order by key').fetchall())")
