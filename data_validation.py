```python
from datetime import date, datetime
from typing import List
from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError, ConfigDict


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str

    model_config = ConfigDict(from_attributes=True)


class Person(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = Field(None, pattern=r'^\\+?1?\\d{10,15}$')
    date_of_birth: date
    address: Address

    @field_validator('date_of_birth')
    @classmethod
    def check_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Person must be at least 18 years old')
        return v

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    order_id: str = Field(..., pattern=r'^ORD-\\d{5}$')
    customer: Person
    items: List[str]
    total_amount: float = Field(..., gt=0)
    created_at: datetime

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not v.startswith('ORD-') or len(v) != 8 or not v[4:].isdigit():
            raise ValueError('order_id must follow pattern ORD-XXXXX where X is digit')
        return v

    model_config = ConfigDict(from_attributes=True)


# Example usage
if __name__ == "__main__":
    # Valid example
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
        date_of_birth=date(1990, 1, 1),
        address=valid_address
    )
    
    valid_order = Order(
        order_id="ORD-12345",
        customer=valid_person,
        items=["Item1", "Item2"],
        total_amount=99.99,
        created_at=datetime.now()
    )
    
    print("Valid Order:", valid_order.model_dump_json(indent=2))
    
    # Invalid examples
    try:
        invalid_order_id = Order(
            order_id="INVALID-123",
            customer=valid_person,
            items=["Item1"],
            total_amount=100.0,
            created_at=datetime.now()
        )
    except ValidationError as e:
        print("Invalid order_id error:", e.errors()[0]['message'])
    
    try:
        invalid_age_person = Person(
            first_name="Kid",
            last_name="Doe",
            email="kid@example.com",
            date_of_birth=date(2020, 1, 1),  # Too young
            address=valid_address
        )
    except ValidationError as e:
        print("Invalid age error:", e.errors()[0]['message'])
    
    try:
        invalid_email_person = Person(
            first_name="Bad",
            last_name="Email",
            email="invalid-email",  # Invalid email
            phone="1234567890",
            date_of_birth=date(1980, 1, 1),
            address=valid_address
        )
    except ValidationError as e:
        print("Invalid email error:", e.errors()[0]['message'])
    
    try:
        invalid_total_order = Order(
            order_id="ORD-00001",
            customer=valid_person,
            items=["Item1"],
            total_amount=-10.0,  # Negative
            created_at=datetime.now()
        )
    except ValidationError as e:
        print("Invalid total_amount error:", e.errors()[0]['message'])
```
