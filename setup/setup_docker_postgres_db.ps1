
<#
.SYNOPSIS

Creates/starts a Docker container named 'postgres_dwdb' using the 'postgres:latest' image,
waits for readiness, and restores the 'dwdb.dump' database into a database named 'dwdb'.

.EXAMPLE
  .\setup_docker_postgres_db.ps1


#>

[CmdletBinding()]
param(
  [string]$Image              = "postgres:latest",
  [string]$Container          = "postgres_dwdb",
  [int]   $HostPort           = 5435,
  [string]$PostgresPassword   = "postgres",
  [string]$PgUser             = "postgres",
  [string]$DbName             = "dwdb",
  [int]   $ReadyTimeoutSecs   = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Dump file is fixed and not exposed as a CLI option
$DumpFile = "dwdb.dump"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 1) Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Err "Docker is not installed or not in PATH."
  exit 1
}

# 2) Pull image (idempotent)
Write-Info "Pulling image $Image ..."
docker pull $Image | Out-Null

# 3) Create or start the container
$containerExists = (docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch $Container -Quiet)
$containerRunning = (docker ps --format '{{.Names}}' | Select-String -SimpleMatch $Container -Quiet)

if ($containerExists) {
  if (-not $containerRunning) {
    Write-Info "Starting existing container '$Container' ..."
    docker start $Container | Out-Null
  } else {
    Write-Info "Container '$Container' already running. Re-using it."
  }
} else {
  Write-Info "Creating and starting container '$Container' ..."
  docker run -p "$HostPort`:5432" `
    --name $Container `
    -e "POSTGRES_PASSWORD=$PostgresPassword" `
    -d $Image | Out-Null
}

# 4) Wait for PostgreSQL readiness (inside container)
Write-Info "Waiting for PostgreSQL to become ready (timeout: $ReadyTimeoutSecs s) ..."
$sw = [Diagnostics.Stopwatch]::StartNew()
$ready = $false
while ($sw.Elapsed.TotalSeconds -lt $ReadyTimeoutSecs) {
  # Run pg_isready and capture its exit code reliably
  $null = docker exec $Container pg_isready -U $PgUser | Out-Null
  $exitCode = $LASTEXITCODE
  if ($exitCode -eq 0) { $ready = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ready) {
  Write-Err "PostgreSQL did not become ready in time."
  exit 1
}
Write-Info "PostgreSQL is ready."

# 5) Validate dump path
if (-not (Test-Path $DumpFile)) {
  Write-Err "Dump file '$DumpFile' not found."
  exit 1
}

# 6) Copy dump into container to avoid Windows newline/encoding issues
$containerDumpPath = "/tmp/restore.dump"
Write-Info "Copying dump to container: $containerDumpPath"
# Remove any existing dump inside the container (ignore errors)
docker exec $Container sh -lc "rm -f $containerDumpPath" | Out-Null
docker cp $DumpFile "$Container`:$containerDumpPath"

# 7) Create DB if not exists
$exists = docker exec -u $PgUser $Container psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DbName}'" | Out-String
$exists = $exists.Trim()
if ($exists -ne "1") {
  Write-Info "Creating database '$DbName' ..."
  docker exec -u $PgUser $Container createdb -U $PgUser $DbName | Out-Null
} else {
  Write-Info "Database '$DbName' already exists. Re-using it."
}

# 8) Restore using container tools
$ext = [IO.Path]::GetExtension($DumpFile).ToLowerInvariant()
Write-Info "Restoring '$DumpFile' into database '$DbName' ..."
if ($ext -eq ".sql") {
  # Plain SQL: use psql -f
  docker exec $Container psql -U $PgUser -d $DbName -f $containerDumpPath
} else {
  # Custom/Tar/Dir dump: use pg_restore
  # Note: directory format would require a copied directory; most users use custom/tar.
  docker exec $Container pg_restore -U $PgUser -d $DbName --clean --if-exists $containerDumpPath
}

# 9) Verify
$verified = docker exec -u $PgUser $Container psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DbName}'" | Out-String
$verified = $verified.Trim()
if ($verified -eq "1") {
  Write-Host "✅ Restore completed." -ForegroundColor Green
  Write-Host "   Connect with: host=localhost port=$HostPort db=$DbName user=$PgUser"
} else {
  Write-Err "Failed to verify database '$DbName'."
  exit 1
}
