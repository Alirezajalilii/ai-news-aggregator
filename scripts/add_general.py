#!/usr/bin/env python3
import asyncio
from src.database.models import Subscription

async def update():
    from src.database.models import get_async_session
    session = await get_async_session()
    async with session:
        from sqlalchemy import select
        result = await session.execute(select(Subscription))
        sub = result.scalar_one()
        sub.categories = ['company', 'research', 'news', 'community', 'general']
        await session.commit()
        print(f'Updated subscription with categories: {sub.categories}')

if __name__ == '__main__':
    asyncio.run(update())