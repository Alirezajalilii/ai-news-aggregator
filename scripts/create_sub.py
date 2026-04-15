#!/usr/bin/env python3
import asyncio
from src.database.models import Subscription

async def create():
    from src.database.models import get_async_session
    session = await get_async_session()
    async with session:
        sub = Subscription(
            subscriber_type='telegram_channel',
            subscriber_id='@ainews_ramzbank',
            categories=['company', 'research', 'news', 'community'],
            frequency='immediate',
            enabled=True
        )
        session.add(sub)
        await session.commit()
        print('Subscription created!')

if __name__ == '__main__':
    asyncio.run(create())