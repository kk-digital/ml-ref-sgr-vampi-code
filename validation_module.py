"""
Data Validation Module using Pydantic

This module provides data validation models for Address, Person, and Order entities
with comprehensive validation rules and custom validators.
"""

from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import re


class Address(BaseModel):
    """Address model with basic location fields."""
    
    street: str = Field(..., min_length=1, description="Street address")
    city: str = Field(..., min_length=1, description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="State code (2 letters)")
    zip_code: str = Field(..., pattern=r'^\d{5}(-\d{4})?$', description="ZIP code (5 or 9 digits)")
    country: str = Field(..., min_length=2, description="Country name")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state code is uppercase."""
        return v.upper()


class Person(BaseModel):
    """Person model with personal information and validation."""
    
    first_name: str = Field(..., min_length=1, description="First name")
    last_name: str = Field(..., min_length=1, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number (optional)")
    date_of_birth: date = Field(..., description="Date of birth")
    address: Address = Field(..., description="Residential address")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v is None:
            return v
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Check if it's a valid phone number (10-15 digits, optional + prefix)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Phone number must contain 10-15 digits, optionally starting with +')
        
        return v
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Ensure person is at least 18 years old."""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        
        if age < 18:
            raise ValueError(f'Person must be at least 18 years old. Current age: {age}')
        
        return v


class Order(BaseModel):
    """Order model with customer information and order details."""
    
    order_id: str = Field(..., description="Order ID in format ORD-XXXXX")
    customer: Person = Field(..., description="Customer information")
    items: List[Any] = Field(..., min_length=1, description="List of order items")
    total_amount: float = Field(..., gt=0, description="Total order amount (must be positive)")
    created_at: datetime = Field(default_factory=datetime.now, description="Order creation timestamp")
    
    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order_id follows pattern ORD-XXXXX where X is a digit."""
        pattern = r'^ORD-\d{5}$'
        if not re.match(pattern, v):
            raise ValueError('order_id must follow pattern ORD-XXXXX (e.g., ORD-12345)')
        
        return v
    
    @model_validator(mode='after')
    def validate_order(self):
        """Additional order-level validation."""
        # Example: Ensure created_at is not in the future
        if self.created_at > datetime.now():
            raise ValueError('created_at cannot be in the future')
        
        return self


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_success_cases():
    """Demonstrate successful validation cases."""
    print("=" * 80)
    print("SUCCESS CASES - Valid Data")
    print("=" * 80)
    
    # Valid Address
    print("\n1. Creating a valid Address:")
    address = Address(
        street="123 Main St",
        city="New York",
        state="ny",  # Will be converted to uppercase
        zip_code="10001",
        country="USA"
    )
    print(f"   [OK] Address created: {address.city}, {address.state} {address.zip_code}")
    
    # Valid Person
    print("\n2. Creating a valid Person:")
    person = Person(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-123-4567",
        date_of_birth=date(1990, 5, 15),
        address=address
    )
    print(f"   [OK] Person created: {person.first_name} {person.last_name}")
    print(f"   [OK] Email: {person.email}")
    print(f"   [OK] Phone: {person.phone}")
    
    # Valid Order
    print("\n3. Creating a valid Order:")
    order = Order(
        order_id="ORD-12345",
        customer=person,
        items=["Item 1", "Item 2", "Item 3"],
        total_amount=299.99
    )
    print(f"   [OK] Order created: {order.order_id}")
    print(f"   [OK] Customer: {order.customer.first_name} {order.customer.last_name}")
    print(f"   [OK] Total: ${order.total_amount}")
    print(f"   [OK] Items count: {len(order.items)}")
    print(f"   [OK] Created at: {order.created_at}")
    
    # Person without optional phone
    print("\n4. Creating a Person without phone (optional field):")
    person_no_phone = Person(
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone=None,
        date_of_birth=date(1985, 3, 20),
        address=address
    )
    print(f"   [OK] Person created: {person_no_phone.first_name} {person_no_phone.last_name}")
    print(f"   [OK] Phone: {person_no_phone.phone}")


def example_failure_cases():
    """Demonstrate validation failure cases."""
    print("\n" + "=" * 80)
    print("FAILURE CASES - Invalid Data")
    print("=" * 80)
    
    # Test 1: Invalid email
    print("\n1. Invalid email format:")
    try:
        Person(
            first_name="John",
            last_name="Doe",
            email="invalid-email",  # Invalid email
            date_of_birth=date(1990, 5, 15),
            address=Address(
                street="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA"
            )
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 2: Invalid phone number
    print("\n2. Invalid phone number:")
    try:
        Person(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="123",  # Too short
            date_of_birth=date(1990, 5, 15),
            address=Address(
                street="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA"
            )
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 3: Person under 18 years old
    print("\n3. Person under 18 years old:")
    try:
        Person(
            first_name="Young",
            last_name="Person",
            email="young@example.com",
            date_of_birth=date(2015, 1, 1),  # Only 10 years old
            address=Address(
                street="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA"
            )
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 4: Invalid order_id pattern
    print("\n4. Invalid order_id pattern:")
    try:
        Order(
            order_id="ORDER-123",  # Wrong pattern
            customer=Person(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                date_of_birth=date(1990, 5, 15),
                address=Address(
                    street="123 Main St",
                    city="New York",
                    state="NY",
                    zip_code="10001",
                    country="USA"
                )
            ),
            items=["Item 1"],
            total_amount=100.0
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 5: Negative total_amount
    print("\n5. Negative total_amount:")
    try:
        Order(
            order_id="ORD-12345",
            customer=Person(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                date_of_birth=date(1990, 5, 15),
                address=Address(
                    street="123 Main St",
                    city="New York",
                    state="NY",
                    zip_code="10001",
                    country="USA"
                )
            ),
            items=["Item 1"],
            total_amount=-50.0  # Negative amount
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 6: Empty items list
    print("\n6. Empty items list:")
    try:
        Order(
            order_id="ORD-12345",
            customer=Person(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                date_of_birth=date(1990, 5, 15),
                address=Address(
                    street="123 Main St",
                    city="New York",
                    state="NY",
                    zip_code="10001",
                    country="USA"
                )
            ),
            items=[],  # Empty list
            total_amount=100.0
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")
    
    # Test 7: Invalid ZIP code
    print("\n7. Invalid ZIP code format:")
    try:
        Address(
            street="123 Main St",
            city="New York",
            state="NY",
            zip_code="ABC123",  # Invalid format
            country="USA"
        )
    except Exception as e:
        print(f"   [FAIL] Validation failed: {e}")


def main():
    """Run all example cases."""
    print("\n" + "PYDANTIC DATA VALIDATION MODULE - EXAMPLES".center(80))
    
    example_success_cases()
    example_failure_cases()
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
