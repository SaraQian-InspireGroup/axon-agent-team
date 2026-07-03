from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def mockup_connection() -> Iterator[psycopg.Connection]:
    url = settings.mockup_database_url or settings.yl_database_url
    if not url:
        raise RuntimeError("MOCKUP_DATABASE_URL or YL_DATABASE_URL is not configured")
    conn = psycopg.connect(url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
