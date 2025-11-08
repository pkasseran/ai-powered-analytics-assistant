<#
.SYNOPSIS
Creates/starts a Docker container named 'postgres_dwdb' using the 'postgres:latest' image,
waits for readiness, restores the 'dwdb.dump' (or .sql) into a database named 'dwdb',
then executes seed SQL inside the container against that database (no local psql required).

.EXAMPLE
  .\setup_docker_postgres_db.ps1
  .\setup_docker_postgres_db.ps1 -SeedSqlPath .\seed_extra.sql
#>

[CmdletBinding()]
param(
  [string]$Image              = "postgres:latest",
  [string]$Container          = "postgres_dwdb",
  [int]   $HostPort           = 5435,
  [string]$PostgresPassword   = "postgres",
  [string]$PgUser             = "postgres",
  [string]$DbName             = "dwdb",
  [int]   $ReadyTimeoutSecs   = 60,

  # Optional: if provided, this SQL file will be executed instead of the built-in seed SQL
  [string]$SeedSqlPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Dump file is fixed and not exposed as a CLI option
$DumpFile = "dwdb.dump"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# -------- Built-in seed SQL (single-quoted here-string: no interpolation) --------
$BuiltInSeedSql = @'
BEGIN;

-- SEED_CURRENT_DATA

WITH dates AS (
  SELECT d::date AS dt
  FROM generate_series(
    (CURRENT_DATE - INTERVAL '540 days')::date,
    CURRENT_DATE + INTERVAL '365 days',
    INTERVAL '1 day'
  ) AS g(d)
)
INSERT INTO dim_date (date, year, month, day)
SELECT cast(dt as date) dt, EXTRACT(YEAR FROM dt)::int, EXTRACT(MONTH FROM dt)::int, EXTRACT(DAY FROM dt)::int
FROM dates
WHERE NOT EXISTS (SELECT 1 FROM dim_date X WHERE X.date = dates.dt)
ORDER BY 1
ON CONFLICT (date) DO NOTHING;

WITH
p AS (SELECT product_sk, product_name, category FROM dim_product),
c AS (SELECT customer_sk, segment FROM dim_customer),
sp AS (SELECT salesperson_sk, region_sk FROM dim_salesperson),
d AS (
  SELECT date_sk, date AS dt
  FROM dim_date
  WHERE date >= cast('2025-09-19' as date) and date < CURRENT_DATE 
    and date_sk > (select max(date_sk) from fact_sales where budget_revenue = 0 )
),
-- category weights
cat_weight AS (
  SELECT category_name AS category,
         CASE category_name
           WHEN 'Electronics' THEN 1.4
           WHEN 'Computers'   THEN 1.2
           WHEN 'Peripherals' THEN 1.0
           WHEN 'Accessories' THEN 0.9
           WHEN 'Wearables'   THEN 0.8
           ELSE 1.0
         END AS w
  FROM dim_category
),
-- customer segment weights
seg_weight AS (
  SELECT DISTINCT segment,
         CASE segment
           WHEN 'Enterprise' THEN 1.4
           WHEN 'Mid-Market' THEN 1.2
           WHEN 'SMB'        THEN 1.0
           WHEN 'Consumer'   THEN 0.8
           ELSE 1.0
         END AS w
  FROM dim_customer
),
prod_cat AS (
  SELECT p.product_sk, p.category, cw.w
  FROM p
  JOIN cat_weight cw ON cw.category = p.category
),
cust_seg AS (
  SELECT c.customer_sk, c.segment, sw.w
  FROM c
  JOIN seg_weight sw ON sw.segment = c.segment
),
base_rows AS (
  SELECT
    d.date_sk,
    d.dt,
    pc.product_sk,
    cs.customer_sk,
    sp.salesperson_sk,
    sp.region_sk,
    -- Quantity: weekday/weekend effect + category & segment weights + modest noise
    GREATEST(
      1,
      ROUND(
        (5 + 5 * (EXTRACT(ISODOW FROM d.dt) BETWEEN 1 AND 5)::int)
        * pc.w
        * cs.w
        * (1 + (random() - 0.5) * 0.6)
      )
    )::int AS quantity,
    -- Unit price baseline by product + small jitter
    ROUND((
      CASE pc.product_sk
        WHEN 1 THEN  799.00
        WHEN 2 THEN  999.00
        WHEN 3 THEN 1199.00
        WHEN 4 THEN 1799.00
        WHEN 5 THEN   99.00
        WHEN 6 THEN  249.00
        WHEN 7 THEN  429.00
        WHEN 8 THEN   59.00
        ELSE          199.00
      END
      * (1 + (random() - 0.5) * 0.04)
    )::numeric, 2) AS unit_price
  FROM d
  JOIN prod_cat pc ON TRUE
  JOIN cust_seg cs ON TRUE
  JOIN sp          ON TRUE
  -- Sparsity control: ~6% of all cartesian combos
  WHERE random() < 0.06
)
INSERT INTO fact_sales
  (product_sk, date_sk, customer_sk, salesperson_sk, region_sk, quantity, unit_price, revenue, sales_cost)
SELECT
  product_sk,
  date_sk,
  customer_sk,
  salesperson_sk,
  region_sk,
  quantity,
  unit_price,
  ROUND((quantity * unit_price)::numeric, 2) AS revenue,
  cast(random() * 35 as numeric(12,2)) as sales_cost
FROM base_rows;

-- Adding budget information
WITH base_budget AS (
  SELECT 
    CAST(date_trunc('month', d3."date") AS date) AS date_month,
    'All Customers ' || d5.segment  AS customer_name,
    'All Products '  || d1.category AS product_name, 
    d2.region_name,
    d4.salesperson_name,
    SUM(f1.revenue * (1 + (random() * 0.30 - 0.15))) AS budget_revenue  -- random factor between -15% and +15%
  FROM fact_sales f1
  LEFT JOIN dim_product     d1 ON (d1.product_sk = f1.product_sk)
  LEFT JOIN dim_region      d2 ON (f1.region_sk = d2.region_sk)
  LEFT JOIN dim_date        d3 ON (f1.date_sk    = d3.date_sk)
  LEFT JOIN dim_salesperson d4 ON (f1.salesperson_sk = d4.salesperson_sk)
  LEFT JOIN dim_customer    d5 ON (f1.customer_sk = d5.customer_sk)
  WHERE 
    f1.date_sk >= (
      SELECT date_sk FROM dim_date WHERE date = (
        SELECT CAST(MAX(date) + interval '1' month AS date)
        FROM fact_sales t1
        INNER JOIN dim_date t2 ON (t1.date_sk = t2.date_sk)
        WHERE budget_revenue <> 0
      )
    )
  GROUP BY 1,2,3,4,5
  ORDER BY 1
)
INSERT INTO fact_sales (product_sk, date_sk, customer_sk, salesperson_sk, region_sk, quantity, unit_price, revenue, sales_cost, budget_revenue)
SELECT 
  T3.product_sk,
  T6.date_sk,
  T2.customer_sk,
  T5.salesperson_sk,
  T4.region_sk,
  0 AS quantity,
  0 AS unit_price,
  0 AS revenue,
  0 AS sales_cost,
  ROUND(budget_revenue) AS budget_revenue
FROM base_budget T1
INNER JOIN dim_customer    T2 ON (T1.customer_name  = T2.customer_name)
INNER JOIN dim_product     T3 ON (T1.product_name   = T3.product_name) 
INNER JOIN dim_region      T4 ON (T1.region_name    = T4.region_name)
INNER JOIN dim_salesperson T5 ON (T1.salesperson_name = T5.salesperson_name)
INNER JOIN dim_date        T6 ON (T1.date_month     = T6."date")
ORDER BY T1.salesperson_name;

COMMIT;
'@

# 1) Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Err "Docker is not installed or not in PATH."
  exit 1
}

# 2) Pull image (idempotent)
Write-Info "Pulling image $Image ..."
docker pull $Image | Out-Null

# 3) Create or start the container
$containerExists  = (docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch $Container -Quiet)
$containerRunning = (docker ps    --format '{{.Names}}' | Select-String -SimpleMatch $Container -Quiet)

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
  if ($LASTEXITCODE -eq 0) { $ready = $true; break }
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
$exists = docker exec -e PGPASSWORD=$PostgresPassword -u $PgUser $Container psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DbName}'" | Out-String
$exists = $exists.Trim()
if ($exists -ne "1") {
  Write-Info "Creating database '$DbName' ..."
  docker exec -e PGPASSWORD=$PostgresPassword -u $PgUser $Container createdb -U $PgUser $DbName | Out-Null
} else {
  Write-Info "Database '$DbName' already exists. Re-using it."
}

# 8) Restore using container tools
$ext = [IO.Path]::GetExtension($DumpFile).ToLowerInvariant()
Write-Info "Restoring '$DumpFile' into database '$DbName' ..."
if ($ext -eq ".sql") {
  docker exec -e PGPASSWORD=$PostgresPassword $Container psql -v ON_ERROR_STOP=1 -U $PgUser -d $DbName -f $containerDumpPath
} else {
  docker exec -e PGPASSWORD=$PostgresPassword $Container pg_restore -U $PgUser -d $DbName --clean --if-exists $containerDumpPath
}

# 9) Verify restore
$verified = docker exec -e PGPASSWORD=$PostgresPassword -u $PgUser $Container psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DbName}'" | Out-String
$verified = $verified.Trim()
if ($verified -ne "1") {
  Write-Err "Failed to verify database '$DbName'."
  exit 1
}
Write-Host "✅ Restore completed." -ForegroundColor Green
Write-Host "   Connect with: host=localhost port=$HostPort db=$DbName user=$PgUser"

# 10) Execute seed SQL (inline or from file) INSIDE the container
if ($SeedSqlPath) {
  if (-not (Test-Path $SeedSqlPath)) {
    Write-Err "SeedSqlPath '$SeedSqlPath' not found."
    exit 1
  }
  $containerSqlPath = "/tmp/seed.sql"
  Write-Info "Copying seed SQL file to container: $containerSqlPath"
  docker exec $Container sh -lc "rm -f $containerSqlPath" | Out-Null
  docker cp $SeedSqlPath "$Container`:$containerSqlPath"

  Write-Info "Running seed SQL from file against '$DbName' ..."
  docker exec -e PGPASSWORD=$PostgresPassword -i $Container psql -v ON_ERROR_STOP=1 -U $PgUser -d $DbName -f $containerSqlPath
} else {
  Write-Info "Running built-in seed SQL against '$DbName' ..."
  # Pipe the here-string directly to psql inside the container
  $BuiltInSeedSql | docker exec -e PGPASSWORD=$PostgresPassword -i $Container psql -v ON_ERROR_STOP=1 -U $PgUser -d $DbName
}

if ($LASTEXITCODE -ne 0) {
  Write-Err "Seed SQL execution failed."
  exit 1
}

Write-Host "✅ Seed SQL executed successfully." -ForegroundColor Green
