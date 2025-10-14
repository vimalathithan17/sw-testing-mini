from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from . import models, schemas

# Business rule: amount stored rounded to 2 decimals, non-negative

def round_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def list_users(db: Session) -> List[models.User]:
    return db.query(models.User).order_by(models.User.id).all()


def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    # Optional explicit user existence check for nicer error
    user = db.get(models.User, order.user_id)
    if not user:
        raise ValueError("foreign key violation: user does not exist")

    amount = round_amount(order.amount)
    if amount < 0:
        raise ValueError("amount must be non-negative")

    db_order = models.Order(user_id=order.user_id, amount=amount)
    db.add(db_order)
    try:
        db.commit()
    except IntegrityError as e:
            db.rollback()
            raise ValueError("integrity error") from e
    db.refresh(db_order)
    return db_order


def list_orders(db: Session) -> List[models.Order]:
    return db.query(models.Order).order_by(models.Order.id).all()
