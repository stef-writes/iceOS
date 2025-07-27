Here's a **mock API template** for a **Facebook Marketplace Seller API**, designed for testing or simulation purposes in agent workflows, automation, or backend services. This template imitates key endpoints a seller might use, assuming features like listing inventory, managing orders, and updating availability.

---

## 🧪 **Mock Facebook Marketplace Seller API**

Base URL: `https://api.mockfbmarketplace.com/v1`

---

### 🔐 Authentication

```http
POST /auth/token
```

**Request:**

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

**Response:**

```json
{
  "access_token": "mock_access_token",
  "expires_in": 3600
}
```

---

### 📦 List Inventory Item

```http
POST /inventory/items
```

**Request:**

```json
{
  "title": "Cordless Drill",
  "description": "Brand new 20V drill with charger",
  "price": 59.99,
  "quantity": 10,
  "condition": "new",
  "category": "Tools",
  "location": {
    "city": "Pittsburgh",
    "state": "PA",
    "zip": "15201"
  },
  "images": [
    "https://images.mockcdn.com/item123-front.jpg"
  ]
}
```

**Response:**

```json
{
  "id": "item_123456",
  "status": "listed",
  "created_at": "2025-07-27T10:00:00Z"
}
```

---

### 🧾 Get All Listings

```http
GET /inventory/items
```

**Response:**

```json
[
  {
    "id": "item_123456",
    "title": "Cordless Drill",
    "price": 59.99,
    "quantity": 10,
    "status": "listed"
  },
  {
    "id": "item_123457",
    "title": "Toolbox - Red",
    "price": 29.99,
    "quantity": 5,
    "status": "sold"
  }
]
```

---

### 🔄 Update Inventory Item

```http
PUT /inventory/items/item_123456
```

**Request:**

```json
{
  "price": 54.99,
  "quantity": 8
}
```

**Response:**

```json
{
  "id": "item_123456",
  "status": "updated"
}
```

---

### ❌ Delete Item

```http
DELETE /inventory/items/item_123456
```

**Response:**

```json
{
  "status": "deleted"
}
```

---

### 📬 Get Inquiries

```http
GET /inquiries
```

**Response:**

```json
[
  {
    "id": "inq_8910",
    "item_id": "item_123456",
    "message": "Is this still available?",
    "buyer_name": "John Smith",
    "timestamp": "2025-07-27T11:05:00Z"
  }
]
```

---

### 🚚 Mark Item as Sold

```http
POST /orders
```

**Request:**

```json
{
  "item_id": "item_123456",
  "quantity_sold": 1,
  "buyer_name": "Jane Doe",
  "sale_price": 59.99,
  "platform": "facebook"
}
```

**Response:**

```json
{
  "order_id": "order_7890",
  "status": "completed"
}
```

---

Would you like this converted into an OpenAPI/Swagger file or mock server using Postman or Mockoon?
