from decimal import Decimal
from app import crud, schemas


def test_amount_rounding_regression(db_session):
    # Guard against regressions: 2-decimal rounding half up
    user = crud.create_user(db_session, schemas.UserCreate(name="Dana"))
    order = crud.create_order(db_session, schemas.OrderCreate(user_id=user.id, amount=Decimal("2.675")))
    assert str(order.amount) == "2.68"  # 2.675 rounds to 2.68 with HALF_UP
