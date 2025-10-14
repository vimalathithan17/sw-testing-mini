from decimal import Decimal
from app import crud, schemas


def test_create_user_and_order(db_session):
    user = crud.create_user(db_session, schemas.UserCreate(name="Alice"))
    assert user.id is not None

    order = crud.create_order(db_session, schemas.OrderCreate(user_id=user.id, amount=Decimal("10.125")))
    assert order.amount == Decimal("10.13")  # rounded half up


def test_create_order_fk_violation(db_session):
    from pytest import raises
    with raises(ValueError):
        crud.create_order(db_session, schemas.OrderCreate(user_id=9999, amount=Decimal("5.00")))


def test_non_negative_amount(db_session):
    from pytest import raises
    user = crud.create_user(db_session, schemas.UserCreate(name="Bob"))
    with raises(ValueError):
        crud.create_order(db_session, schemas.OrderCreate(user_id=user.id, amount=Decimal("-1.00")))
