#!/usr/bin/env bash
set -euo pipefail

# --- Config (tweak as needed) ---
IMAGE="postgres:latest"
CONTAINER="postgres_dwdb"
HOST_PORT=5435               # host port → container 5432
POSTGRES_PASSWORD="postgres" # superuser password for the container
PGUSER="postgres"
DB_NAME="dwdb"
DUMP_FILE="${1:-dwdb.dump}"  # pass path to dump as arg1 or defaults to dwdb.dump
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
DB_EXISTS=$(docker exec -u "${PGUSER}" "${CONTAINER}" \
  psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)
if [[ "${DB_EXISTS}" != "1" ]]; then
  echo "Creating database '${DB_NAME}'..."
  docker exec -u "${PGUSER}" "${CONTAINER}" createdb -U "${PGUSER}" "${DB_NAME}"
else
  echo "Database '${DB_NAME}' already exists. Re-using it."
fi

# 7) Restore into the database using tools from the container
#    - If the dump looks like a plain SQL file (.sql), use psql
#    - Otherwise assume pg_dump custom/dir/tar and use pg_restore
echo "Restoring '${DUMP_FILE}' into '${DB_NAME}'..."

if [[ "${DUMP_FILE}" == *.sql ]]; then
  # Plain SQL dump: stream to psql inside the container
  docker exec -i "${CONTAINER}" psql -U "${PGUSER}" -d "${DB_NAME}" < "${DUMP_FILE}"
else
  # Custom/dir/tar dump: stream to pg_restore inside the container
  # --clean/--if-exists makes the restore idempotent-ish by dropping objects first if present
  docker exec -i "${CONTAINER}" pg_restore -U "${PGUSER}" -d "${DB_NAME}" --clean --if-exists < "${DUMP_FILE}"
fi

# 8) Verify DB presence from inside the container
DB_EXISTS=$(docker exec -u "${PGUSER}" "${CONTAINER}" \
  psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)
if [[ "${DB_EXISTS}" == "1" ]]; then
  echo "Database '${DB_NAME}' is present."
else
  echo "Failed to verify database '${DB_NAME}'." >&2
  exit 1
fi

echo "✅ PostgreSQL setup and restore completed successfully."
echo "   Host connection:  localhost:${HOST_PORT}"
echo "   Database name:    ${DB_NAME}"
