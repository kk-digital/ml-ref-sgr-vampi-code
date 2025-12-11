from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import List, Optional
from pydantic import ValidationError

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
        if v is not None:
            import re
            if not re.match(r'^\\+?1?\\d{9,15}$', v):
                raise ValueError('Phone number must be a valid format (e.g., +1234567890)')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def check_age(cls, v):
        today = date.today()
        age_days = (today - v).days
        if age_days < 18 * 365.25:
            raise ValueError('Person must be at least 18 years old')
        return v

class Order(BaseModel):
    order_id: str
    customer: Person
    items: List[str]
    total_amount: float = Field(gt=0)
    created_at: date

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v):
        import re
        if not re.match(r'^ORD-\\d{5}$', v):
            raise ValueError('order_id must follow the pattern ORD-XXXXX where X is a digit')
        return v

if __name__ == "__main__":
    print("=== Example Usage ===")
    
    # Success case
    print("\n1. Success Case:")
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
        phone="+1-234-567-8900",
        date_of_birth=date(1990, 1, 1),
        address=valid_address
    )
    valid_order = Order(
        order_id="ORD-12345",
        customer=valid_person,
        items=["Laptop", "Mouse"],
        total_amount=1299.99,
        created_at=date.today()
    )
    print("✅ Valid Order:", valid_order.model_dump_json(indent=2))
    
    # Failure cases
    print("\n2. Invalid order_id:")
    try:
        invalid_order1 = Order(
            order_id="ORD-ABC12",
            customer=valid_person,
            items=["Item"],
            total_amount=100.0,
            created_at=date.today()
        )
    except ValidationError as e:
        print("❌ Caught ValidationError:", str(e.errors()[0]))
    
    print("\n3. Invalid total_amount (negative):")
    try:
        invalid_order2 = Order(
            order_id="ORD-12345",
            customer=valid_person,
            items=["Item"],
            total_amount=-50.0,
            created_at=date.today()
        )
    except ValidationError as e:
        print("❌ Caught ValidationError:", str(e.errors()[0]))
    
    print("\n4. Invalid email in person:")
    invalid_person = Person(
        first_name="Jane",
        last_name="Doe",
        email="invalid-email",
        phone="1234567890",
        date_of_birth=date(2008, 1, 1),  # Under 18 in 2025
        address=valid_address
    )
    try:
        invalid_order3 = Order(
            order_id="ORD-54321",
            customer=invalid_person,
            items=["Item"],
            total_amount=100.0,
            created_at=date.today()
        )
    except ValidationError as e:
        print("❌ Caught ValidationError (multiple):", [err['message'] for err in e.errors()])
    
    print("\n5. Invalid phone:")
    try:
        person_with_bad_phone = Person(
            first_name="Bob",
            last_name="Smith",
            email="bob@example.com",
            phone="invalid",
            date_of_birth=date(1980, 1, 1),
            address=valid_address
        )
    except ValidationError as e:
        print("❌ Invalid phone caught:", str(e.errors()[0]))