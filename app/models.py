from datetime import datet
from sqlalchemy import Column, Integer, String, Date,Numeric, ForeignKey
from database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    salary = Column(Numeric(10, 2), nullable=False)
    hire_date = Column(Date, nullable=False)

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    sale_date = Column(Date, nullable=False)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    order_amount = Column(Numeric(10, 2), nullable=False)
    order_date = Column(Date, nullable=False)
