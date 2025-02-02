from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from database.models import Inventory  # Import your Inventory model
from database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

class InventoryCreate(BaseModel):
    name: str
    quantity: int
    unit: str

class InventoryUpdate(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the inventory item")
    quantity: int = Field(..., gt=0, description="Quantity of the inventory item")
    unit: str = Field(..., min_length=1, description="Unit of the inventory item")

# Fetch all inventory items
@router.get("/")
async def get_inventory(db: AsyncSession = Depends(get_db)):
    items = await db.execute(select(Inventory))
    return [item.to_dict() for item in items.scalars().all()]

# Add a new inventory item
@router.post("/", response_model=InventoryCreate)
async def add_inventory_item(item: InventoryCreate, db: AsyncSession = Depends(get_db)):
    new_item = Inventory(name=item.name, quantity=item.quantity, unit=item.unit)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item.to_dict()

# Edit an existing inventory item
@router.put("/{item_id}", response_model=InventoryUpdate)
async def edit_inventory_item(item_id: int, item: InventoryUpdate, db: AsyncSession = Depends(get_db)):
    existing_item = await db.get(Inventory, item_id)
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item.name = item.name
    existing_item.quantity = item.quantity
    existing_item.unit = item.unit
    await db.commit()
    return existing_item.to_dict()

# Delete an inventory item
@router.delete("/{item_id}")
async def delete_inventory_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(Inventory, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return {"detail": "Item deleted"}
