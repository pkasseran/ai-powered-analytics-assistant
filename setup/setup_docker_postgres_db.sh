#!/usr/bin/env bash
set -euo pipefail

# --- Config (tweak as needed) ---
IMAGE="postgres:latest"
CONTAINER="postgres_dwdb"
HOST_PORT=5435               # host port → container 5432
POSTGRES_PASSWORD="postgres" # superuser password for the container
PGUSER="postgres"
DB_NAME="dwdb"
DUMP_FILE="${1:-dwdb.dump}"  # arg1: path to dump (default: dwdb.dump)
SEED_SQL_FILE="${2:-}"       # arg2 (optional): path to seed SQL to run; if empty, use built-in SQL
# -------------------------------

# 1) Require Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed." >&2
  exit 1
fi

# 2) Pull image (idempotent)
echo "Pulling image ${IMAGE}..."
docker pull "${IMAGE}"

# 3) Create or start the postgres container
if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    echo "Container '${CONTAINER}' is already running. Re-using it."
  else
    echo "Starting existing container '${CONTAINER}'..."
    docker start "${CONTAINER}" >/dev/null
  fi
else
  echo "Creating and starting container '${CONTAINER}'..."
  docker run -p "${HOST_PORT}:5432" \
    --name "${CONTAINER}" \
    -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
    -d "${IMAGE}" >/dev/null
fi

# 4) Wait for PostgreSQL to become ready (using tools inside the container)
echo "Waiting for PostgreSQL to become ready..."
for i in {1..60}; do
  if docker exec "${CONTAINER}" pg_isready -U "${PGUSER}" >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  sleep 1
  if [[ $i -eq 60 ]]; then
    echo "PostgreSQL did not become ready in time." >&2
    exit 1
  fi
done

# 5) Ensure dump file exists on the host
if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "Error: dump file '${DUMP_FILE}' not found." >&2
  exit 1
fi

# 6) Create database inside the container if it doesn't already exist
DB_EXISTS=$(docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -u "${PGUSER}" "${CONTAINER}" \
  psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true | tr -d '[:space:]')
if [[ "${DB_EXISTS}" != "1" ]]; then
  echo "Creating database '${DB_NAME}'..."
  docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -u "${PGUSER}" "${CONTAINER}" createdb -U "${PGUSER}" "${DB_NAME}"
else
  echo "Database '${DB_NAME}' already exists. Re-using it."
fi

# 7) Restore into the database using tools from the container
#    - If the dump looks like a plain SQL file (.sql), use psql
#    - Otherwise assume pg_dump custom/dir/tar and use pg_restore
echo "Restoring '${DUMP_FILE}' into '${DB_NAME}'..."
if [[ "${DUMP_FILE}" == *.sql ]]; then
  docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -i "${CONTAINER}" \
    psql -v ON_ERROR_STOP=1 -U "${PGUSER}" -d "${DB_NAME}" < "${DUMP_FILE}"
else
  docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -i "${CONTAINER}" \
    pg_restore -U "${PGUSER}" -d "${DB_NAME}" --clean --if-exists < "${DUMP_FILE}"
fi

# 8) Verify DB presence from inside the container
DB_EXISTS=$(docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -u "${PGUSER}" "${CONTAINER}" \
  psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true | tr -d '[:space:]')
if [[ "${DB_EXISTS}" != "1" ]]; then
  echo "Failed to verify database '${DB_NAME}'." >&2
  exit 1
fi
echo "✅ Restore complete."

# 9) Run seed SQL (from file if provided, else built-in)
echo "Running seed SQL against '${DB_NAME}'..."
if [[ -n "${SEED_SQL_FILE}" ]]; then
  if [[ ! -f "${SEED_SQL_FILE}" ]]; then
    echo "Error: seed SQL file '${SEED_SQL_FILE}' not found." >&2
    exit 1
  fi
  docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -i "${CONTAINER}" \
    psql -v ON_ERROR_STOP=1 -U "${PGUSER}" -d "${DB_NAME}" < "${SEED_SQL_FILE}"
else
  # Built-in seed SQL (literal heredoc to avoid host-side expansion)
  docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" -i "${CONTAINER}" \
    psql -v ON_ERROR_STOP=1 -U "${PGUSER}" -d "${DB_NAME}" <<'SQL_EOF'
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
SQL_EOF
fi

echo "✅ Seed SQL executed successfully."
echo "   Host connection:  localhost:${HOST_PORT}"
echo "   Database name:    ${DB_NAME}"
