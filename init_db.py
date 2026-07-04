import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection - Use raw password for psycopg2
DB_NAME = 'controlbook'
DB_USER = 'controlbook_user'
DB_PASSWORD = 'John@4598'  # Raw password for psycopg2
DB_HOST = 'localhost'
DB_PORT = '5432'

def get_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def init_database():
    """Create tables"""
    try:
        conn = get_connection()
        if not conn:
            return
            
        cur = conn.cursor()
        
        # Create products table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                category VARCHAR(100) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create transactions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                type VARCHAR(20) NOT NULL CHECK (type IN ('sale', 'restock')),
                quantity INTEGER NOT NULL,
                price DECIMAL(10, 2),
                revenue DECIMAL(10, 2),
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert sample products
        cur.execute("""
            INSERT INTO products (name, category, quantity, price) 
            VALUES 
                ('Laptop', 'Electronics', 10, 999.99),
                ('Mouse', 'Electronics', 50, 29.99),
                ('Keyboard', 'Electronics', 30, 79.99),
                ('Monitor', 'Electronics', 15, 299.99)
            ON CONFLICT (name) DO NOTHING
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database tables created successfully!")
        print("✅ Sample products added!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    init_database()
