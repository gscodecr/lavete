from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.orders import Order

router = APIRouter()

@router.get("/orders")
async def debug_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).order_by(Order.id.desc()).limit(10))
    orders = result.scalars().all()
    return [{"id": o.id, "status": o.status, "payment_proof": o.payment_proof, "pending": o.pending_receipt_url} for o in orders]
