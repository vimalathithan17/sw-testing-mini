from fastapi import FastAPI, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from .db import Base, engine, SessionLocal
from . import crud, models, schemas

# Create tables if not existing (for demo). In production, use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SW Testing Mini App")

# UI setup
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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

# -------------------- UI Views --------------------
@app.get("/ui", response_class=HTMLResponse)
async def ui_index(request: Request, q: str = "", db: Session = Depends(get_db)):
    users = crud.list_users(db)
    orders = crud.list_orders(db)
    search_results = None
    if q:
        search_results = db.query(models.User).filter(models.User.name.like(f"%{q}%")).all()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "users": users, "orders": orders, "q": q, "search_results": search_results, "error": None},
    )

@app.post("/ui/users")
async def ui_create_user(name: str = Form(...), email: str | None = Form(default=None), db: Session = Depends(get_db)):
    crud.create_user(db, schemas.UserCreate(name=name, email=email or None))
    return RedirectResponse(url="/ui", status_code=303)

@app.post("/ui/orders")
async def ui_create_order(request: Request, user_id: int = Form(...), amount: str = Form(...), db: Session = Depends(get_db)):
    try:
        crud.create_order(db, schemas.OrderCreate(user_id=user_id, amount=amount))
        return RedirectResponse(url="/ui", status_code=303)
    except ValueError as e:
        # Re-render with error message
        users = crud.list_users(db)
        orders = crud.list_orders(db)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "users": users, "orders": orders, "q": "", "search_results": None, "error": str(e)},
            status_code=400,
        )
