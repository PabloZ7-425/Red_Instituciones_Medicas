$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$privado = Join-Path $raiz '.local/datos-de-prueba'
$entorno = Join-Path $raiz '.env'
if (-not (Test-Path -LiteralPath $entorno -PathType Leaf)) {
    throw 'Prepara el archivo .env siguiendo el README de la raíz.'
}

Push-Location -LiteralPath $raiz
try {
    $servicios = @(docker compose --env-file .env ps --status running --services)
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no está disponible.' }
    $faltantes = @('backend', 'postgres', 'mysql', 'mongo', 'firestore') | Where-Object { $_ -notin $servicios }
    if ($faltantes) { throw "Inicia los servicios del README antes de cargar los datos. Faltan $($faltantes -join ', ')." }

    New-Item -ItemType Directory -Force -Path $privado | Out-Null
    docker compose --env-file .env run --rm --no-deps -T -e PYTHONPATH=/app `
        -v "${PSScriptRoot}:/datos:ro" -v "${privado}:/accesos" `
        backend python -B /datos/carga.py --accesos /accesos/accesos.json
    if ($LASTEXITCODE -ne 0) { throw 'La carga se detuvo. Corrige el paso indicado y vuelve a ejecutarla.' }
    Write-Output "Accesos locales guardados en $privado/accesos.json"
} finally {
    Pop-Location
}
