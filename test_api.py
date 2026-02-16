import requests

BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "admin@lavete.com"
PASSWORD = "admin123"

def test_flow():
    # 1. Login
    print("Logging in...")
    login_data = {"username": EMAIL, "password": PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. List Products
    print("Fetching products...")
    response = requests.get(f"{BASE_URL}/products/", headers=headers)
    print(f"Products: {response.json()}")
    products = response.json()
    if not products:
        print("No products found.")
        return
    product_id = products[0]["id"]

    # 3. Create Customer
    print("Creating customer...")
    customer_data = {"full_name": "Juan Perez", "email": "juan@example.com"}
    response = requests.post(f"{BASE_URL}/customers/", json=customer_data, headers=headers)
    if response.status_code not in [200, 201]:
        print(f"Customer creation failed: {response.status_code} - {response.text}")
        return

    print(f"Customer created: {response.json()}")
    customer_id = response.json().get("id")

    # 4. Create Order
    print("Creating order...")
    order_data = {"customer_id": customer_id}
    response = requests.post(f"{BASE_URL}/orders/", json=order_data, headers=headers)
    print(f"Order created: {response.json()}")
    order_id = response.json()["id"]

    # 5. Add Item
    print("Adding item...")
    item_data = {"product_id": product_id, "quantity": 1}
    response = requests.post(f"{BASE_URL}/orders/{order_id}/items", json=item_data, headers=headers)
    
    if response.status_code == 200:
        print(f"Item added. Order: {response.json()}")
    else:
        print(f"Failed to add item: {response.text}")

    # 6. Confirm Order
    print("Confirming order...")
    response = requests.post(f"{BASE_URL}/orders/{order_id}/confirm", headers=headers)
    print(f"Order confirmed: {response.json()}")

if __name__ == "__main__":
    try:
        test_flow()
    except Exception as e:
        print(f"Test failed: {e}")
