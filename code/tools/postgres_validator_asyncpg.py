import asyncpg

async def validate_sql(uri: str, sql: str) -> tuple[bool, dict | None]:
    conn = await asyncpg.connect(uri)
    try:
        await conn.prepare(sql)
        return True, None
    except asyncpg.PostgresError as e:
        return False, {"code": e.sqlstate, "message": e.message}
    finally:
        await conn.close()
