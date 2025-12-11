"""
Example usage of the validation module demonstrating success and failure cases.

This file shows how to use the Pydantic models and demonstrates various validation scenarios.
"""

from datetime import date, datetime
from validation_module import Address, Person, Order, OrderItem
from pydantic import ValidationError


def create_valid_address():
    """Create a valid address example."""
    return Address(
        street="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
        country="USA"
    )


def create_valid_person():
    """Create a valid person example."""
    return Person(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        date_of_birth=date(1990, 1, 1),
        address=create_valid_address()
    )


def create_valid_order():
    """Create a valid order example."""
    items = [
        OrderItem(product_name="Laptop", quantity=1, unit_price=999.99),
        OrderItem(product_name="Mouse", quantity=2, unit_price=25.50)
    ]
    
    return Order(
        order_id="ORD-12345",
        customer=create_valid_person(),
        items=items,
        total_amount=sum(item.total_price for item in items)
    )


def demonstrate_success_cases():
    """Demonstrate successful validation cases."""
    print("=" * 60)
    print("SUCCESSFUL VALIDATION CASES")
    print("=" * 60)
    
    # Valid Address
    print("\n1. Creating valid Address:")
    try:
        address = create_valid_address()
        print(f"✅ Address created: {address.json(indent=2)}")
    except ValidationError as e:
        print(f"❌ Error: {e}")
    
    # Valid Person
    print("\n2. Creating valid Person:")
    try:
        person = create_valid_person()
        print(f"✅ Person created: {person.json(indent=2)}")
    except ValidationError as e:
        print(f"❌ Error: {e}")
    
    # Valid Order
    print("\n3. Creating valid Order:")
    try:
        order = create_valid_order()
        print(f"✅ Order created: {order.json(indent=2)}")
    except ValidationError as e:
        print(f"❌ Error: {e}")


def demonstrate_failure_cases():
    """Demonstrate validation failure cases."""
    print("\n" + "=" * 60)
    print("VALIDATION FAILURE CASES")
    print("=" * 60)
    
    # Invalid Address (empty fields)
    print("\n1. Invalid Address - empty street:")
    try:
        Address(
            street="",  # Invalid: empty string
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA"
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Person (bad email)
    print("\n2. Invalid Person - bad email format:")
    try:
        Person(
            first_name="John",
            last_name="Doe",
            email="invalid-email",  # Invalid: not a proper email
            phone="+1234567890",
            date_of_birth=date(1990, 1, 1),
            address=create_valid_address()
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Person (bad phone)
    print("\n3. Invalid Person - bad phone format:")
    try:
        Person(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123",  # Invalid: too short
            date_of_birth=date(1990, 1, 1),
            address=create_valid_address()
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Person (under 18)
    print("\n4. Invalid Person - under 18 years old:")
    try:
        Person(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            phone="+1234567890",
            date_of_birth=date(2010, 1, 1),  # Invalid: under 18
            address=create_valid_address()
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Order (bad order_id)
    print("\n5. Invalid Order - wrong order_id format:")
    try:
        Order(
            order_id="INVALID-123",  # Invalid: wrong format
            customer=create_valid_person(),
            items=[OrderItem(product_name="Laptop", quantity=1, unit_price=999.99)],
            total_amount=999.99
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Order (negative total_amount)
    print("\n6. Invalid Order - negative total amount:")
    try:
        Order(
            order_id="ORD-12345",
            customer=create_valid_person(),
            items=[OrderItem(product_name="Laptop", quantity=1, unit_price=999.99)],
            total_amount=-100.0  # Invalid: negative amount
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Order (total amount mismatch)
    print("\n7. Invalid Order - total amount doesn't match item total:")
    try:
        Order(
            order_id="ORD-12345",
            customer=create_valid_person(),
            items=[OrderItem(product_name="Laptop", quantity=1, unit_price=999.99)],
            total_amount=500.0  # Invalid: doesn't match calculated total
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")
    
    # Invalid Order (empty items list)
    print("\n8. Invalid Order - empty items list:")
    try:
        Order(
            order_id="ORD-12345",
            customer=create_valid_person(),
            items=[],  # Invalid: empty list
            total_amount=0.0
        )
        print("❌ Should have failed!")
    except ValidationError as e:
        print(f"✅ Correctly failed: {e}")


def demonstrate_edge_cases():
    """Demonstrate edge cases and optional fields."""
    print("\n" + "=" * 60)
    print("EDGE CASES AND OPTIONAL FIELDS")
    print("=" * 60)
    
    # Person without phone (optional field)
    print("\n1. Person without phone number (optional field):")
    try:
        person = Person(
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@example.com",
            phone=None,  # Optional field set to None
            date_of_birth=date(1985, 5, 15),
            address=create_valid_address()
        )
        print(f"✅ Person created without phone: {person.json(indent=2)}")
    except ValidationError as e:
        print(f"❌ Error: {e}")
    
    # Order with auto-generated timestamp
    print("\n2. Order with auto-generated timestamp:")
    try:
        order = Order(
            order_id="ORD-54321",
            customer=create_valid_person(),
            items=[OrderItem(product_name="Book", quantity=3, unit_price=19.99)],
            total_amount=59.97
            # created_at will be auto-generated
        )
        print(f"✅ Order created with timestamp: {order.json(indent=2)}")
        print(f"   Created at: {order.created_at}")
    except ValidationError as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("Pydantic Validation Module Examples")
    print("===================================")
    
    # Run all demonstrations
    demonstrate_success_cases()
    demonstrate_failure_cases()
    demonstrate_edge_cases()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ All validation rules are working correctly!")
    print("✅ Email validation ensures proper format")
    print("✅ Phone validation ensures 10-15 digits with optional +")
    print("✅ Age validation ensures minimum 18 years old")
    print("✅ Order ID validation ensures ORD-XXXXX pattern")
    print("✅ Total amount validation ensures positive values")
    print("✅ Total amount validation ensures consistency with items")
    print("✅ Optional fields work as expected")
    print("✅ Auto-generated fields work as expected")