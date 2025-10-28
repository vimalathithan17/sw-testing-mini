from fastapi import FastAPI, Depends, HTTPException, Query, Request, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from .db import Base, engine, SessionLocal
from . import crud, models, schemas
from . import config
from .utils import sanitize_input
from .auth import create_access_token, decode_access_token
from sqlalchemy import text
import os
from fastapi import Header

# Create tables if not existing (for demo). In production, use Alembic.
Base.metadata.create_all(bind=engine)

# Ensure `role` and `password_hash` columns exist on users table for older DB files used in tests/dev.
with engine.connect() as conn:
    try:
        res = conn.execute(text("PRAGMA table_info(users)"))
        cols = [row[1] for row in res.fetchall()]
        if 'role' not in cols:
            # SQLite supports ADD COLUMN; set default to 'user'
            conn.execute(text("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user' NOT NULL"))
        if 'password_hash' not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash TEXT"))
        # Backfill any NULLs just in case
        conn.execute(text("UPDATE users SET role='user' WHERE role IS NULL"))
        conn.commit()
    except Exception:
        # If the users table doesn't exist yet or pragma failed, ignore
        pass

app = FastAPI(title="SW Testing Mini App")

# Initialize runtime vulnerable flag from environment (can be toggled at runtime)
env_vuln = os.getenv("VULNERABLE", "0")
config.set_vulnerable(env_vuln in ("1", "true", "True"))

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


@app.get("/search_vuln", response_model=List[schemas.UserRead])
async def search_users_vuln(q: str = Query("", min_length=0, max_length=200), db: Session = Depends(get_db)):
    """A toggleable endpoint that demonstrates vulnerable vs safe search.

    - If `config.is_vulnerable()` is True, we run a raw SQL query built with f-strings
      (intentionally vulnerable to SQL injection for testing).
    - If False, we use a ORM/parameterized query.
    """
    if not q:
        return []
    if config.is_vulnerable():
        # Vulnerable: build SQL with direct interpolation (DO NOT DO THIS IN REAL APPS)
        sql = f"SELECT id, name, email, role FROM users WHERE name = '{q}'"
        rows = db.execute(text(sql)).all()
        # Map rows to UserRead-like dicts
        results = []
        for r in rows:
            results.append(models.User(id=r[0], name=r[1], email=r[2], role=(r[3] if len(r) > 3 else 'user')))
        return results
    else:
        # Safe: parameterized ORM filter for exact match
        return db.query(models.User).filter(models.User.name == q).all()


@app.get("/users/{user_id}", response_model=schemas.UserDetail)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_with_orders(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    # ensure orders are loaded
    return user


@app.delete("/orders/{order_id}")
async def api_delete_order(order_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_order(db, order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="order not found")
    return {"deleted": order_id}


@app.put("/orders/{order_id}")
async def api_update_order(order_id: int, payload: dict, db: Session = Depends(get_db), x_acting_user_id: int | None = Header(default=None), request: Request = None):
    # payload may contain 'amount'
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")

    # Authorization: acting user must be the order owner or an admin
    # resolve acting user id from Authorization or header
    acting_id = None
    auth = None
    if request:
        auth = request.headers.get('authorization')
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1]
        try:
            payload_token = decode_access_token(token)
            acting_id = int(payload_token.get('sub'))
        except Exception:
            raise HTTPException(status_code=401, detail='invalid token')
    elif x_acting_user_id is not None:
        acting_id = int(x_acting_user_id)

    if acting_id is None:
        raise HTTPException(status_code=403, detail="missing acting user header or token")
    acting = db.get(models.User, acting_id)
    if not acting:
        raise HTTPException(status_code=403, detail="acting user not found")
    if acting.role != 'admin' and acting.id != order.user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    amount = payload.get('amount')
    try:
        updated = crud.update_order(db, order_id, amount=amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated


@app.delete("/users/{user_id}")
async def api_delete_user(user_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="user not found")
    return {"deleted": user_id}


@app.put("/users/{user_id}")
async def api_update_user(user_id: int, payload: dict, db: Session = Depends(get_db), x_acting_user_id: int | None = Header(default=None), request: Request = None):
    # Accept raw dict to keep things simple for this small app
    name = payload.get("name")
    email = payload.get("email")
    role = payload.get("role")

    # perform update
    updated = crud.update_user(db, user_id, name=name, email=email)
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")

    # role changes require admin privilege
    if role is not None:
        # resolve acting user: prefer Authorization bearer token, fall back to X-Acting-User-Id
        acting_id = None
        # check Authorization
        auth = None
        if request:
            auth = request.headers.get('authorization')
        if auth and auth.lower().startswith('bearer '):
            token = auth.split(None, 1)[1]
            try:
                payload_token = decode_access_token(token)
                acting_id = int(payload_token.get('sub'))
            except Exception:
                raise HTTPException(status_code=401, detail='invalid token')
        elif x_acting_user_id is not None:
            acting_id = int(x_acting_user_id)

        if acting_id is None:
            raise HTTPException(status_code=403, detail="missing acting user header or token")
        acting = db.get(models.User, acting_id)
        if not acting or acting.role != 'admin':
            raise HTTPException(status_code=403, detail="forbidden: admin required to change role")
        try:
            updated = crud.update_user_role(db, user_id, role)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return updated


@app.get("/ui/users/{user_id}", response_class=HTMLResponse)
async def ui_user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_with_orders(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "users": crud.list_users(db), "orders": crud.list_orders(db), "q": "", "search_results": None, "error": "user not found", "vulnerable": config.is_vulnerable()},
            status_code=404,
        )
    return templates.TemplateResponse(
        "user_detail.html",
        {"request": request, "user": user, "vulnerable": config.is_vulnerable()},
    )


@app.post("/ui/users/{user_id}/orders")
async def ui_create_order_for_user(request: Request, user_id: int, amount: str = Form(...), db: Session = Depends(get_db)):
    # Create order then redirect back to user detail
    try:
        crud.create_order(db, schemas.OrderCreate(user_id=user_id, amount=amount))
        return RedirectResponse(url=f"/ui/users/{user_id}", status_code=303)
    except ValueError as e:
        users = crud.list_users(db)
        orders = crud.list_orders(db)
        return templates.TemplateResponse(
            "user_detail.html",
            {"request": request, "user": crud.get_user_with_orders(db, user_id), "error": str(e), "vulnerable": config.is_vulnerable()},
            status_code=400,
        )


@app.get("/vulnerable")
async def get_vulnerable():
    return {"vulnerable": config.is_vulnerable()}


@app.post("/vulnerable")
async def set_vulnerable_endpoint(request: Request):
    """Set the runtime vulnerable flag. Accepts value via query, form, or JSON body.

    This flexible input handling lets the same endpoint be used by tests
    (query param), by UI forms (form data), and by programmatic clients (JSON).
    """
    # Try query param first
    value = request.query_params.get("value")
    # Then form data
    if value is None:
        try:
            form = await request.form()
            value = form.get("value")
        except Exception:
            value = None

    # Then JSON body
    if value is None:
        try:
            body = await request.json()
            if isinstance(body, dict):
                value = body.get("value")
        except Exception:
            pass

    # Parse boolean-ish values
    val = False
    if isinstance(value, str):
        val = value.lower() in ("1", "true", "yes", "on")
    elif isinstance(value, bool):
        val = value
    elif value is not None:
        # Fallback: truthy conversion
        val = bool(value)

    config.set_vulnerable(val)
    return {"vulnerable": config.is_vulnerable()}


@app.post("/auth/login")
async def auth_login(payload: dict, db: Session = Depends(get_db)):
    # Support two flows:
    # 1) legacy: { "user_id": <int> } -> return token for that user if no password is set (backwards compatible)
    # 2) secure: { "user_id": <int>, "password": "..." } -> verify password and return token
    uid = payload.get("user_id")
    if uid is None:
        raise HTTPException(status_code=400, detail="user_id required")
    user = db.get(models.User, int(uid))
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    pwd = payload.get('password')
    # if user has password_hash, require password; otherwise allow legacy user_id flow
    if user.password_hash:
        if not pwd:
            raise HTTPException(status_code=401, detail="password required")
        from .auth import verify_password
        if not verify_password(pwd, user.password_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")
    # legacy flow allowed when no password_hash present and no password provided
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer"}

# -------------------- UI Views --------------------
@app.get("/ui", response_class=HTMLResponse)
async def ui_index(request: Request, q: str = "", db: Session = Depends(get_db)):
    users = crud.list_users(db)
    orders = crud.list_orders(db)
    search_results = None
    toast = None
    if q:
        sanitized_q = sanitize_input(q)
        toast = None
        if not config.is_vulnerable() and sanitized_q != (q or ""):
            # Input was cleaned in safe mode — inform the user and use the sanitized value
            toast = "Invalid input detected — input has been sanitized for safety."
        search_results = db.query(models.User).filter(models.User.name.like(f"%{sanitized_q}%")).all()
    return templates.TemplateResponse(
        "index.html",
            {
                "request": request,
                "users": users,
                "orders": orders,
                "q": q,
                "search_results": search_results,
                "error": None,
                "toast": toast,
                "vulnerable": config.is_vulnerable(),
            },
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
