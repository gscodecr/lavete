import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text("SELECT id, status, pending_receipt_url, payment_proof FROM orders ORDER BY id DESC LIMIT 5"))
        print(result.fetchall())

asyncio.run(main())
