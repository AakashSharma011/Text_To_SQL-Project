import random
from datetime import date, timedelta
from .database import admin_engine, AdminSession,Base
from sqlalchemy.orm import Session
from models import Employee, Sale, Order

FIRST_NAMES = ["Aarav", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Rohan", "Meera"]
LAST_NAMES = ["Sharma", "Patel", "Gupta", "Singh", "Kumar", "Verma"]
DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Finance", "HR", "Operations"]
CUSTOMER_COMPANIES = ["TechCorp", "DataDriven Inc.", "CloudNine Solutions", "GreenLeaf Retail"]

def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0,delta))

def _seed_employees(session:Session,count:int=25)->list[int]:
    random.seed(42)
    salary_ranges = {
        "Engineering": (75_000, 150_000), "Sales": (50_000, 110_000),
        "Marketing": (55_000, 105_000), "Finance": (65_000, 130_000),
        "HR": (50_000, 95_000), "Operations": (45_000, 90_000),
    }
    ids = []
    for i in range(count):
        dept = DEPARTMENTS[i % len(DEPARTMENTS)]
        low, high = salary_ranges[dept]
        emp = Employee(
            name=f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[i % len(LAST_NAMES)]}",
            department=dept,
            salary=round(random.uniform(low, high), 2),
            hire_date=_random_date(date(2019, 1, 1), date(2025, 12, 31)),
        )
        session.add(emp)
        session.flush()
        ids.append(emp.id)
    return ids

def _seed_sales(session: Session, employee_ids: list[int], count: int = 40) -> None:
    for _ in range(count):
        session.add(Sale(
            employee_id=random.choice(employee_ids),
            amount=round(random.uniform(500, 50_000), 2),
            sale_date=_random_date(date(2024, 1, 1), date(2025, 12, 31)),
        ))


def _seed_orders(session: Session, count: int = 30) -> None:
    for _ in range(count):
        session.add(Order(
            customer_name=random.choice(CUSTOMER_COMPANIES),
            order_amount=round(random.uniform(1_000, 100_000), 2),
            order_date=_random_date(date(2024, 1, 1), date(2025, 12, 31)),
        ))

def run_seed() -> None:
    Base.metadata.create_all(admin_engine)  # tables banao agar exist nahi karte
    with AdminSession() as session:
        existing = session.query(Employee).count()
        if existing > 0:
            print(f"Already seeded ({existing} employees). Skipping.")
            return
        emp_ids = _seed_employees(session)
        _seed_sales(session, emp_ids)
        _seed_orders(session)
        session.commit()
        print("Seed done: 25 employees, 40 sales, 30 orders.")


if __name__ == "__main__":
    run_seed()    


