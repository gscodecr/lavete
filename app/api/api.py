from fastapi import APIRouter
from app.api.endpoints import auth, products, customers, orders, users, chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# Pets are handled via customers endpoint (nested) or we can expose them if needed.
# For now, pets creation is in customers.py router.
