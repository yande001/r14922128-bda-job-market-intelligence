"""PostgreSQL access for the API: a tiny pooled query helper."""
from __future__ import annotations

import os

from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

_pool: SimpleConnectionPool | None = None


def _get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            1,
            10,
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ.get("POSTGRES_DB", "jobmarket"),
            user=os.environ.get("POSTGRES_USER", "jobmarket"),
            password=os.environ.get("POSTGRES_PASSWORD", "jobmarket"),
        )
    return _pool


def query(sql: str, params: tuple = ()) -> list[dict]:
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        pool.putconn(conn)
