import psycopg
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Connection string
conn_str = f"dbname=recdesk_app user={os.getenv('DB_USER')} password={os.getenv('DB_PASSWORD')} host=localhost"

# Global pool
pool = AsyncConnectionPool(conn_str, open=False)

async def get_conn():
    async with pool.connection() as conn:
        yield conn