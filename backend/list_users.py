import asyncio
from sqlalchemy import select

from app.models.database import User, get_async_session

async def main():
    async with get_async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"\nFound {len(users)} users:\n")

        for user in users:
            print("----------------------------")
            print("Email :", user.email)
            print("Name  :", user.name)
            print("ID    :", user.id)

asyncio.run(main())
