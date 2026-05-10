import os
import asyncpg
import asyncio

def read_db_pw() -> str:
    file_path = ".secrets/db_password"
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Secret file not found at {file_path}")

async def clean():
    conn = await asyncpg.connect(
        user=os.getenv("DB_USER"),
        password=read_db_pw(),
        database=os.getenv("DB_NAME"),
        host="localhost",
        port=os.getenv("DB_PORT")
    )
    await conn.execute("TRUNCATE TABLE users CASCADE;")
    await conn.close()

asyncio.run(clean())