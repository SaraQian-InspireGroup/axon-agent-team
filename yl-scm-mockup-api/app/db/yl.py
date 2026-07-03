from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def yl_connection() -> Iterator[psycopg.Connection]:
    if not settings.yl_database_url:
        raise RuntimeError("YL_DATABASE_URL is not configured")
    conn = psycopg.connect(settings.yl_database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def check_yl_db() -> str:
    if not settings.yl_database_url:
        return "skip"
    try:
        with yl_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return "ok"
    except Exception:
        return "error"
