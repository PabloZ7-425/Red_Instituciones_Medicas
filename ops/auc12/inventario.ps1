# Read-only: never starts/stops services, applies migrations or exports patient rows.
[CmdletBinding()]
param([string]$ProjectName = '')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$compose = @('compose', '--project-directory', $repo, '--file', (Join-Path $repo 'docker-compose.yml'))
if ($ProjectName) { $compose += @('--project-name', $ProjectName) }
$ids = @(& docker @compose ps -q backend)
if ($LASTEXITCODE -ne 0 -or $ids.Count -ne 1 -or -not $ids[0]) {
    throw 'No se encontro un backend activo de este proyecto. Inicia tu instalacion habitual o indica -ProjectName; este script no levanta servicios.'
}
$previousEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $source = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_inventory.py') -Raw
    $raw = $source | & docker exec -i $ids[0] python -B -
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo ejecutar el inventario de solo lectura en el backend.' }
    $report = ($raw -join "`n") | ConvertFrom-Json
    if ($report.read_only -ne $true) { throw 'El reporte no tiene el formato esperado.' }
    $folder = Join-Path $repo '.local/auc12'
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    $name = 'inventario-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + ([Guid]::NewGuid().ToString('N').Substring(0,8)) + '.json'
    $path = Join-Path $folder $name
    [IO.File]::WriteAllText($path, ($report | ConvertTo-Json -Depth 25), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host 'Inventario terminado. No se modificaron bases ni servicios.'
    Write-Host 'Comparte unicamente este reporte tecnico (sin contrasenas ni registros de pacientes):'
    Write-Host $path
} finally { $OutputEncoding = $previousEncoding }
