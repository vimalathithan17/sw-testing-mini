from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .db import Base, engine, SessionLocal
from . import crud, models, schemas

# Create tables if not existing (for demo). In production, use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SW Testing Mini App")

# Dependency to get DB session per request

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/users", response_model=schemas.UserRead, status_code=201)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    created = crud.create_user(db, user)
    return created

@app.get("/users", response_model=List[schemas.UserRead])
async def get_users(db: Session = Depends(get_db)):
    return crud.list_users(db)

@app.post("/orders", response_model=schemas.OrderRead, status_code=201)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        created = crud.create_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return created

@app.get("/orders", response_model=List[schemas.OrderRead])
async def get_orders(db: Session = Depends(get_db)):
    return crud.list_orders(db)

@app.get("/search", response_model=List[schemas.UserRead])
async def search_users(q: str = Query("", min_length=0, max_length=100), db: Session = Depends(get_db)):
    # Black-box injection safe: ORM filter with parameterization
    if not q:
        return []
    results = db.query(models.User).filter(models.User.name.like(f"%{q}%")).all()
    return results
