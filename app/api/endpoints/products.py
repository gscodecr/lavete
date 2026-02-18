from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models import Product, User
from app.schemas import products
from app.api import deps

router = APIRouter()

@router.get("/")
async def read_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    stock_low: bool = False,
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to return (e.g. sku,name,price)"),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Product)
    
    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%")
            )
        )
    if category:
        query = query.where(Product.category == category)
    if stock_low:
        query = query.where(Product.stock <= Product.min_stock)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    if fields:
        field_list = [f.strip() for f in fields.split(',')]
        return [
            {k: getattr(item, k, None) for k in field_list if hasattr(item, k)}
            for item in items
        ]
    
    return items

@router.post("/", response_model=products.Product)
async def create_product(
    product_in: products.ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    # Check if SKU exists
    result = await db.execute(select(Product).where(Product.sku == product_in.sku))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Product with this SKU already exists"
        )
        
    db_product = Product(**product_in.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/{product_id}", response_model=products.Product)
async def read_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=products.Product)
async def update_product(
    product_id: int,
    product_in: products.ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    await db.commit()
    await db.refresh(product)
    return product
    await db.commit()
    await db.refresh(product)
    return product

@router.get("/export/json")
async def export_products_json(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    # return as list of dicts
    return [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "stock": p.stock,
            "min_stock": p.min_stock,
            "price": float(p.price),
            "brand": p.brand,
            "image_url": p.image_url,
            "description": p.description,
            "is_active": p.is_active
        }
        for p in products
    ]

@router.post("/import/json")
async def import_products_json(
    products_in: List[products.ProductCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    Import products from JSON list. 
    Updates if SKU exists, creates if not.
    """
    count_created = 0
    count_updated = 0
    
    for p_in in products_in:
        # Check if exists by SKU
        result = await db.execute(select(Product).where(Product.sku == p_in.sku))
        existing_product = result.scalars().first()
        
        if existing_product:
            # Update
            update_data = p_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(existing_product, field, value)
            count_updated += 1
        else:
            # Create
            db_product = Product(**p_in.model_dump())
            db.add(db_product)
            count_created += 1
            
    await db.commit()
    return {"message": "Import successful", "created": count_created, "updated": count_updated}
