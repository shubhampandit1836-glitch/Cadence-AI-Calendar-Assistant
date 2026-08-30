import os
import psycopg2  # pyright: ignore[reportMissingModuleSource]
import psycopg2.pool  # pyright: ignore[reportMissingModuleSource]

_connection_pool = None

def init_pool():
    global _connection_pool
    if _connection_pool is None:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL is not set.")
        _connection_pool = psycopg2.pool.SimpleConnectionPool(1, 20, db_url)
    return _connection_pool

def get_connection():
    return init_pool().getconn()

def release_connection(conn):
    if _connection_pool and conn:
        _connection_pool.putconn(conn)