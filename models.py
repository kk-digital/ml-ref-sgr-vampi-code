from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date, datetime
from typing import List, Optional
import re

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str

class Person(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: date
    address: Address

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        pattern = r'^\+?\d[\d\s\-\(\)]{9,16}$'
        if not re.match(pattern, v):
            raise ValueError('Phone number must be a valid format (10-15 digits with optional + and separators)')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def check_min_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Person must be at least 18 years old')
        return v

class Order(BaseModel):
    order_id: str
    customer: Person
    items: List[str]
    total_amount: float = Field(gt=0)
    created_at: datetime

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v):
        if not re.match(r'^ORD-\\d{5}$', v):
            raise ValueError('order_id must follow the pattern "ORD-XXXXX" where X are digits')
        return v

# Example usage demonstrating validation success and failure cases
if __name__ == "__main__":
    print("=== SUCCESS CASE ===")
    valid_address = Address(
        street="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
        country="USA"
    )
    valid_person = Person(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-123-4567",
        date_of_birth=date(1990, 5, 15),  # Over 18
        address=valid_address
    )
    valid_order = Order(
        order_id="ORD-12345",
        customer=valid_person,
        items=["Laptop", "Mouse"],
        total_amount=1250.75,
        created_at=datetime.now()
    )
    print("Valid Order:", valid_order.model_dump_json(indent=2))

    print("\n=== FAILURE CASES ===")
    
    # Invalid email
    try:
        invalid_email_person = Person(
            first_name="Jane",
            last_name="Doe",
            email="invalid-email",
            phone="+1-555-123-4567",
            date_of_birth=date(1990, 5, 15),
            address=valid_address
        )
    except Exception as e:
        print("1. Invalid email:", str(e))

    # Invalid phone
    try:
        invalid_phone_person = Person(
            first_name="Bob",
            last_name="Smith",
            email="bob.smith@example.com",
            phone="invalid_phone",
            date_of_birth=date(1990, 5, 15),
            address=valid_address
        )
    except Exception as e:
        print("2. Invalid phone:", str(e))

    # Underage
    try:
        underage_person = Person(
            first_name="Kid",
            last_name="Doe",
            email="kid@example.com",
            phone=None,
            date_of_birth=date(2010, 1, 1),  # Under 18
            address=valid_address
        )
    except Exception as e:
        print("3. Underage:", str(e))

    # Invalid order_id
    try:
        invalid_order = Order(
            order_id="INVALID-123",
            customer=valid_person,
            items=["Item"],
            total_amount=100.0,
            created_at=datetime.now()
        )
    except Exception as e:
        print("4. Invalid order_id:", str(e))

    # Negative total
    try:
        negative_order = Order(
            order_id="ORD-67890",
            customer=valid_person,
            items=["Item"],
            total_amount=-50.0,
            created_at=datetime.now()
        )
    except Exception as e:
        print("5. Negative total_amount:", str(e))
