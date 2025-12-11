"""
Data Validation Module using Pydantic

This module provides data validation models for Address, Person, and Order entities
with comprehensive validation rules.
"""

from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator, Field
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
        """Ensure state is uppercase."""
        return v.upper()


class Person(BaseModel):
    """Person model with personal information and age validation."""
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
        
        # Check if it's a valid phone number (10-15 digits, optionally starting with +)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Phone number must be 10-15 digits, optionally starting with +')
        
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
    """Order model with customer information and validation rules."""
    order_id: str = Field(..., description="Order ID following pattern ORD-XXXXX")
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
            raise ValueError(
                f'order_id must follow pattern ORD-XXXXX (e.g., ORD-12345). Got: {v}'
            )
        return v


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_success_case():
    """Demonstrate successful validation."""
    print("=" * 70)
    print("SUCCESS CASE: Valid data")
    print("=" * 70)
    
    try:
        # Create a valid address
        address = Address(
            street="123 Main St",
            city="New York",
            state="ny",  # Will be converted to uppercase
            zip_code="10001",
            country="USA"
        )
        
        # Create a valid person (born in 1990, definitely 18+)
        person = Person(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            date_of_birth=date(1990, 5, 15),
            address=address
        )
        
        # Create a valid order
        order = Order(
            order_id="ORD-12345",
            customer=person,
            items=["Item 1", "Item 2", "Item 3"],
            total_amount=99.99
        )
        
        print("✓ Order created successfully!")
        print(f"\nOrder ID: {order.order_id}")
        print(f"Customer: {order.customer.first_name} {order.customer.last_name}")
        print(f"Email: {order.customer.email}")
        print(f"Phone: {order.customer.phone}")
        print(f"Address: {order.customer.address.street}, {order.customer.address.city}, {order.customer.address.state}")
        print(f"Items: {len(order.items)} items")
        print(f"Total: ${order.total_amount:.2f}")
        print(f"Created: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")


def example_failure_cases():
    """Demonstrate various validation failures."""
    print("\n" + "=" * 70)
    print("FAILURE CASES: Invalid data")
    print("=" * 70)
    
    # Test 1: Invalid email
    print("\n1. Testing invalid email...")
    try:
        address = Address(
            street="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA"
        )
        person = Person(
            first_name="Jane",
            last_name="Smith",
            email="invalid-email",  # Invalid email
            date_of_birth=date(1990, 1, 1),
            address=address
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 2: Invalid phone number
    print("\n2. Testing invalid phone number...")
    try:
        person = Person(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            phone="123",  # Too short
            date_of_birth=date(1990, 1, 1),
            address=address
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 3: Person under 18
    print("\n3. Testing person under 18 years old...")
    try:
        person = Person(
            first_name="Young",
            last_name="Person",
            email="young@example.com",
            date_of_birth=date(2015, 1, 1),  # Only 10 years old
            address=address
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 4: Invalid order_id pattern
    print("\n4. Testing invalid order_id pattern...")
    try:
        person = Person(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth=date(1990, 1, 1),
            address=address
        )
        order = Order(
            order_id="INVALID-123",  # Wrong pattern
            customer=person,
            items=["Item 1"],
            total_amount=50.0
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 5: Negative total_amount
    print("\n5. Testing negative total_amount...")
    try:
        order = Order(
            order_id="ORD-12345",
            customer=person,
            items=["Item 1"],
            total_amount=-10.0  # Negative amount
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 6: Empty items list
    print("\n6. Testing empty items list...")
    try:
        order = Order(
            order_id="ORD-12345",
            customer=person,
            items=[],  # Empty list
            total_amount=50.0
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 7: Invalid ZIP code
    print("\n7. Testing invalid ZIP code...")
    try:
        address = Address(
            street="123 Main St",
            city="New York",
            state="NY",
            zip_code="ABCDE",  # Invalid ZIP
            country="USA"
        )
        print("✗ Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")


def example_optional_phone():
    """Demonstrate optional phone field."""
    print("\n" + "=" * 70)
    print("OPTIONAL FIELD: Person without phone number")
    print("=" * 70)
    
    try:
        address = Address(
            street="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001",
            country="USA"
        )
        
        person = Person(
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            # phone is optional, not provided
            date_of_birth=date(1985, 3, 20),
            address=address
        )
        
        print("✓ Person created successfully without phone number!")
        print(f"Name: {person.first_name} {person.last_name}")
        print(f"Email: {person.email}")
        print(f"Phone: {person.phone}")  # Will be None
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")


if __name__ == "__main__":
    # Run all examples
    example_success_case()
    example_failure_cases()
    example_optional_phone()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
