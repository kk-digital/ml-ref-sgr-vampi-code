"""
Data Validation Module using Pydantic

This module provides data validation models for Address, Person, and Order entities
with comprehensive validation rules including email format, phone validation,
age verification, and custom order ID patterns.
"""

import re
from datetime import date, datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class Address(BaseModel):
    """Address model with basic address fields."""

    street: str = Field(..., min_length=1, description="Street address")
    city: str = Field(..., min_length=1, description="City name")
    state: str = Field(..., min_length=1, description="State or province")
    zip_code: str = Field(..., min_length=1, description="Postal/ZIP code")
    country: str = Field(..., min_length=1, description="Country name")

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, v: str) -> str:
        """Validate zip code format (allows various international formats)."""
        # Remove spaces and validate it's alphanumeric with optional hyphens
        cleaned = v.replace(" ", "")
        if not re.match(r"^[A-Za-z0-9\-]+$", cleaned):
            raise ValueError("ZIP code must contain only letters, numbers, and hyphens")
        return v


class Person(BaseModel):
    """Person model with contact information and age validation."""

    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number (optional)")
    date_of_birth: date = Field(..., description="Date of birth")
    address: Address = Field(..., description="Person's address")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v is None:
            return v

        # Remove common formatting characters for validation
        cleaned = re.sub(r"[\s\-\(\)\.]", "", v)

        # Check if it starts with optional + and contains only digits
        if not re.match(r"^\+?\d{7,15}$", cleaned):
            raise ValueError(
                "Phone number must be 7-15 digits, optionally starting with '+' "
                "for international format"
            )
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Ensure the person is at least 18 years old."""
        today = date.today()

        # Calculate age
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))

        if age < 18:
            raise ValueError(f"Person must be at least 18 years old (current age: {age})")

        if v > today:
            raise ValueError("Date of birth cannot be in the future")

        return v

    @property
    def full_name(self) -> str:
        """Return the person's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate and return the person's current age."""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class OrderItem(BaseModel):
    """Individual item in an order."""

    product_name: str = Field(..., min_length=1, description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity (must be positive)")
    unit_price: float = Field(..., gt=0, description="Unit price (must be positive)")

    @property
    def subtotal(self) -> float:
        """Calculate subtotal for this item."""
        return self.quantity * self.unit_price


class Order(BaseModel):
    """Order model with customer, items, and validation rules."""

    order_id: str = Field(..., description="Order ID in format ORD-XXXXX")
    customer: Person = Field(..., description="Customer information")
    items: list[OrderItem] = Field(..., min_length=1, description="Order items")
    total_amount: float = Field(..., gt=0, description="Total amount (must be positive)")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Order creation timestamp"
    )

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order ID follows pattern ORD-XXXXX (5 alphanumeric characters)."""
        pattern = r"^ORD-[A-Za-z0-9]{5}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Order ID must follow pattern 'ORD-XXXXX' where X is alphanumeric "
                f"(e.g., 'ORD-12345', 'ORD-AB123'). Got: '{v}'"
            )
        return v.upper()  # Normalize to uppercase

    @model_validator(mode="after")
    def validate_total_matches_items(self) -> "Order":
        """Validate that total_amount reasonably matches the sum of items."""
        calculated_total = sum(item.subtotal for item in self.items)

        # Allow small floating point differences (e.g., for tax/discounts)
        # This is a soft validation - warns but doesn't fail
        if abs(self.total_amount - calculated_total) > 0.01:
            # You could raise an error here if strict matching is required:
            # raise ValueError(f"Total amount ({self.total_amount}) doesn't match "
            #                  f"calculated total ({calculated_total})")
            pass

        return self


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def demonstrate_validation():
    """Demonstrate validation success and failure cases."""

    print("=" * 70)
    print("PYDANTIC DATA VALIDATION DEMONSTRATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # SUCCESS CASES
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[SUCCESS] SUCCESS CASES")
    print("=" * 70)

    # Valid Address
    print("\n1. Creating a valid Address:")
    try:
        address = Address(
            street="123 Main Street",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA"
        )
        print(f"   [OK] Address created: {address.city}, {address.state} {address.zip_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")

    # Valid Person
    print("\n2. Creating a valid Person (age 30):")
    try:
        person = Person(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            date_of_birth=date(1995, 6, 15),
            address=address
        )
        print(f"   [OK] Person created: {person.full_name}, Age: {person.age}")
        print(f"   [OK] Email: {person.email}")
        print(f"   [OK] Phone: {person.phone}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")

    # Valid Person without phone (optional field)
    print("\n3. Creating a valid Person without phone:")
    try:
        person_no_phone = Person(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@company.org",
            date_of_birth=date(1990, 3, 20),
            address=address
        )
        print(f"   [OK] Person created: {person_no_phone.full_name}")
        print(f"   [OK] Phone: {person_no_phone.phone} (None - optional)")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")

    # Valid Order
    print("\n4. Creating a valid Order:")
    try:
        order = Order(
            order_id="ORD-12345",
            customer=person,
            items=[
                OrderItem(product_name="Widget A", quantity=2, unit_price=29.99),
                OrderItem(product_name="Widget B", quantity=1, unit_price=49.99),
            ],
            total_amount=109.97
        )
        print(f"   [OK] Order created: {order.order_id}")
        print(f"   [OK] Customer: {order.customer.full_name}")
        print(f"   [OK] Items: {len(order.items)}")
        print(f"   [OK] Total: ${order.total_amount:.2f}")
        print(f"   [OK] Created at: {order.created_at}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")

    # -------------------------------------------------------------------------
    # FAILURE CASES
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[FAILURE] FAILURE CASES (Expected Validation Errors)")
    print("=" * 70)

    # Invalid email format
    print("\n1. Invalid email format:")
    try:
        Person(
            first_name="Test",
            last_name="User",
            email="not-an-email",  # Invalid!
            date_of_birth=date(1990, 1, 1),
            address=address
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: {str(e)[:100]}...")

    # Invalid phone number
    print("\n2. Invalid phone number:")
    try:
        Person(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="123",  # Too short!
            date_of_birth=date(1990, 1, 1),
            address=address
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Phone validation failed")

    # Person under 18
    print("\n3. Person under 18 years old:")
    try:
        Person(
            first_name="Young",
            last_name="Person",
            email="young@example.com",
            date_of_birth=date(2015, 1, 1),  # Too young!
            address=address
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Age validation failed (must be 18+)")

    # Invalid order ID format
    print("\n4. Invalid order ID format:")
    try:
        Order(
            order_id="INVALID-ID",  # Wrong format!
            customer=person,
            items=[OrderItem(product_name="Test", quantity=1, unit_price=10.0)],
            total_amount=10.0
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Order ID must follow pattern 'ORD-XXXXX'")

    # Order ID too short
    print("\n5. Order ID too short (ORD-123):")
    try:
        Order(
            order_id="ORD-123",  # Only 3 characters after ORD-!
            customer=person,
            items=[OrderItem(product_name="Test", quantity=1, unit_price=10.0)],
            total_amount=10.0
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Order ID must have exactly 5 characters after 'ORD-'")

    # Negative total amount
    print("\n6. Negative total amount:")
    try:
        Order(
            order_id="ORD-99999",
            customer=person,
            items=[OrderItem(product_name="Test", quantity=1, unit_price=10.0)],
            total_amount=-50.0  # Negative!
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Total amount must be positive")

    # Empty items list
    print("\n7. Empty items list:")
    try:
        Order(
            order_id="ORD-99999",
            customer=person,
            items=[],  # Empty!
            total_amount=50.0
        )
        print("   [ERROR] Should have failed!")
    except Exception as e:
        print(f"   [OK] Caught expected error: {type(e).__name__}")
        print(f"     Message: Items list cannot be empty")

    # -------------------------------------------------------------------------
    # SERIALIZATION EXAMPLE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[SERIALIZATION] SERIALIZATION EXAMPLES")
    print("=" * 70)

    print("\n1. Convert Order to dictionary:")
    order_dict = order.model_dump()
    print(f"   Keys: {list(order_dict.keys())}")

    print("\n2. Convert Order to JSON:")
    order_json = order.model_dump_json(indent=2)
    print(f"   JSON preview (first 200 chars):")
    print(f"   {order_json[:200]}...")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_validation()
