import asyncio
from sqlalchemy import text

from app.models.database import get_async_session

async def main():
    async with get_async_session() as session:
        result = await session.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname='public'
            ORDER BY tablename;
        """))

        for row in result:
            print(row[0])

asyncio.run(main())