from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    # Added in V2 via migration; defined here but migration handles existing DBs
    email = Column(String, nullable=True, unique=False, index=True)
    # role column for simple RBAC: 'user' or 'admin'
    role = Column(String, nullable=False, default='user', index=True)
    # password hash (bcrypt). Nullable for legacy users created without password
    password_hash = Column(String, nullable=True)

    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)

    user = relationship("User", back_populates="orders")
