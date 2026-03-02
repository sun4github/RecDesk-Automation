import psycopg
from psycopg_pool import AsyncConnectionPool

# Connection string
conn_str = "dbname=recdesk_app user=user_ai password=SMACK!small3bright host=localhost"

# Global pool
pool = AsyncConnectionPool(conn_str, open=False)

async def get_conn():
    async with pool.connection() as conn:
        yield conn