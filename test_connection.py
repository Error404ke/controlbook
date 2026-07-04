import ssl
import sys
from pymongo import MongoClient
from urllib.parse import quote_plus

print(f"Python version: {sys.version}")

# Your credentials
username = "johndere404_db_user"
password = "19aZRvSFYlaguyQ5"
cluster = "cluster0.pgc5t8p.mongodb.net"

# Create a custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Build connection string
uri = f"mongodb+srv://{username}:{quote_plus(password)}@{cluster}/?retryWrites=true&w=majority&appName=Cluster0"

try:
    # Connect with custom SSL context
    client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000
    )
    
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully!")
    
    db = client.msfavour
    collections = db.list_collection_names()
    print(f"📁 Collections: {collections}")
    
    count = db.products.count_documents({})
    print(f"📦 Products: {count}")
    
    if count > 0:
        for p in db.products.find():
            print(f"  - {p['name']}: {p['quantity']} units")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
