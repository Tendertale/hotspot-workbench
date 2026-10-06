param(
    [int]$Port = 8000,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $SkipBuild) {
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        npm run build
    }
    finally {
        Pop-Location
    }
}

Set-Location $projectRoot
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port

