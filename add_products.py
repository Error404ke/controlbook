import ssl
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Your connection string
uri = 'mongodb+srv://johndere404_db_user:19aZRvSFYlaguyQ5@cluster0.pgc5t8p.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'

# Connect with proper settings
client = MongoClient(
    uri,
    server_api=ServerApi('1'),
    tls=True,
    tlsAllowInvalidCertificates=True,  # This helps with SSL issues
    connectTimeoutMS=30000,
    socketTimeoutMS=30000
)

# Get database
db = client.msfavour

print("✅ Connected to MongoDB Atlas!")

# List collections
collections = db.list_collection_names()
print(f"Collections: {collections}")

# Check if products collection exists, if not create it
if 'products' not in collections:
    db.create_collection('products')
    print("✅ Created 'products' collection")
if 'transactions' not in collections:
    db.create_collection('transactions')
    print("✅ Created 'transactions' collection")

# Sample products
products = [
    {"name": "Laptop", "category": "Electronics", "quantity": 10, "price": 999.99},
    {"name": "Mouse", "category": "Electronics", "quantity": 50, "price": 29.99},
    {"name": "Keyboard", "category": "Electronics", "quantity": 30, "price": 79.99},
    {"name": "Monitor", "category": "Electronics", "quantity": 15, "price": 299.99},
]

# Insert products
for product in products:
    existing = db.products.find_one({"name": product["name"]})
    if existing:
        print(f"⏭️  Product '{product['name']}' already exists")
    else:
        result = db.products.insert_one(product)
        print(f"✅ Added: {product['name']}")

# Show products
print("\n📦 Products in database:")
for p in db.products.find():
    print(f"  - {p['name']}: {p['quantity']} units @ ${p['price']}")

print(f"\n📊 Total products: {db.products.count_documents({})}")
