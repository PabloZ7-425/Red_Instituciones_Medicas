# Verifies host backups on the existing SQL servers, using original local owners.
# No migrations, password changes, source writes, container rebuilds or new engines.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BackupDir,
    [string]$ProjectName = 'red_instituciones_medicas',
    [string]$SourceRef = 'FETCH_HEAD'
)
$ErrorActionPreference='Stop'
$repo=(Get-Location).Path
if (-not (Test-Path (Join-Path $repo 'docker-compose.yml'))) { throw 'Ejecuta desde la carpeta del repositorio.' }
$backup=(Resolve-Path -LiteralPath $BackupDir).Path
foreach ($file in @('hospital.dump','identidad.dump','pediatrico.sql')) {
    $item=Get-Item -LiteralPath (Join-Path $backup $file)
    if ($item.Length -le 0) { throw "Respaldo vacio: $file" }
}
$ref=@(& git rev-parse --verify $SourceRef)
if ($LASTEXITCODE -ne 0 -or $ref.Count -ne 1 -or $ref[0] -notmatch '^[a-f0-9]{40}$') { throw 'Ref Git no valido.' }
$ref=$ref[0]
$tag=[Guid]::NewGuid().ToString('N')
$work=Join-Path $repo ('.local/auc12/verificacion-'+$tag)
New-Item -ItemType Directory -Path $work | Out-Null
$utf8=New-Object System.Text.UTF8Encoding($false)
$compose=@('compose','--project-directory',$repo,'--file',(Join-Path $repo 'docker-compose.yml'),'-p',$ProjectName)
$results=@()
$report=[ordered]@{source_ref=$ref;original_databases_modified=$false;status='running';copies=@()}
$reportPath=Join-Path $work 'verificacion-respaldos.json'
function Save-Report {
    $report.copies=@($results)
    [IO.File]::WriteAllText($reportPath,($report | ConvertTo-Json -Depth 15),$utf8)
}
function Asset([string]$name) {
    $text=@(& git show "${ref}:ops/auc12/$name")
    if ($LASTEXITCODE -ne 0) { throw "No se pudo leer $name de Git." }
    return (($text -join "`n")+"`n")
}
function Invoke-Docker([string[]]$Arguments, [AllowNull()][string]$InputText=$null) {
    # Capture native stderr rather than letting PowerShell 5 print SQL details.
    $ErrorActionPreference='Continue'
    if ($null -ne $InputText) { $lines=@($InputText | & docker @Arguments 2>&1) }
    else { $lines=@(& docker @Arguments 2>&1) }
    return [pscustomobject]@{Code=$LASTEXITCODE;Lines=$lines}
}
function Docker-Checked([string[]]$Arguments) {
    $reply=Invoke-Docker -Arguments $Arguments
    if ($reply.Code -ne 0) { throw 'Fallo una operacion Docker; no se aplicaron migraciones al origen.' }
    return $reply.Lines
}

$previousEncoding=$OutputEncoding
try {
    $OutputEncoding=$utf8
    foreach ($service in @('postgres','identidad','mysql')) {
        $listing=Invoke-Docker -Arguments ($compose+@('ps','-q',$service))
        $ids=@($listing.Lines)
        if ($listing.Code -ne 0 -or $ids.Count -ne 1 -or $ids[0] -notmatch '^[a-f0-9]{64}$') { throw "No se encontro un contenedor activo para $service." }
        $id=$ids[0]
        $source=(@{postgres='hospital';identidad='identidad';mysql='pediatrico'})[$service]
        $file=(@{postgres='hospital.dump';identidad='identidad.dump';mysql='pediatrico.sql'})[$service]
        $prefix=(@{postgres='test_b3_auc12_';identidad='test_auc12_identity_';mysql='test_b4_auc12_'})[$service]
        $copy=$prefix+$tag.Substring(0,16)
        $remote='/tmp/auc12_verify_'+$tag
        $path=Join-Path $backup $file
        $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        Docker-Checked -Arguments @('exec',$id,'mkdir','-m','700',$remote) | Out-Null
        $remoteFile='backup.dump';$job='restore_postgres_copy.sh'
        if ($service -eq 'mysql') { $remoteFile='backup.sql';$job='restore_mysql_copy.sh' }
        Docker-Checked -Arguments @('cp',$path,"${id}:$remote/$remoteFile") | Out-Null
        if ($service -ne 'mysql') {
            $check=Join-Path $work 'postgres_fingerprint.sql'
            [IO.File]::WriteAllText($check,(Asset 'postgres_fingerprint.sql'),$utf8)
            Docker-Checked -Arguments @('cp',$check,"${id}:$remote/postgres_fingerprint.sql") | Out-Null
        }
        Write-Host "Verificando respaldo $source en $copy..."
        $script=Asset $job
        # Windows pipelines append CRLF. Normalize inside the Linux container.
        $reply=Invoke-Docker -InputText $script -Arguments @('exec','-i','-e',"AUC12_SOURCE_DB=$source",'-e',"AUC12_COPY_DB=$copy",'-e',"AUC12_WORK=$remote",'-e',"AUC12_ARCHIVE_SHA=$hash",$id,'sh','-c',"tr -d '\015' | sh")
        $output=@($reply.Lines)
        if ($reply.Code -ne 0) {
            [IO.File]::WriteAllText((Join-Path $work ($service+'-error-privado.log')),($output -join "`n"),$utf8)
            throw "No se verifico $source. El detalle privado quedo en $work. No compartas dumps ni logs privados completos."
        }
        $fingerprint=@($output | Where-Object { "$_" -match '^[a-f0-9]{64}$' })
        if ($fingerprint.Count -ne 1) { throw "Respuesta de verificacion inesperada en $source." }
        $method='PostgreSQL: hashes agregados de todas las tablas y estado de secuencias'
        if ($service -eq 'mysql') { $method='MySQL: cantidad y CHECKSUM EXTENDED por tabla; SHA256 del manifiesto' }
        $results+= [ordered]@{source_database=$source;copy_database=$copy;archive_sha256=$hash;restored_and_compared=$true;comparison_fingerprint="$($fingerprint[0])";method=$method;permissions_acceptance_verified=$false}
        Save-Report
        Write-Host "OK: $source restaurado y contenido comparado."
    }
    $report.status='verified';Save-Report
    Write-Host 'Comparte solamente el reporte tecnico:'
    Write-Host $reportPath
    Write-Host 'Las copias se conservan para ensayar migraciones. No se modificaron las bases originales.'
} catch {
    $report.status='incomplete';Save-Report
    Write-Host "Reporte parcial: $reportPath"
    throw
} finally { $OutputEncoding=$previousEncoding }
