import os
import io
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from openpyxl import Workbook
import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# PostgreSQL Configuration - Use Render's Database URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Use the full database URL from Render
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Fallback for local development
    DB_USER = os.environ.get('DB_USER', 'controlbook_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'John@4598')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'controlbook')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===== MODELS =====
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='product', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'quantity': self.quantity,
            'price': float(self.price)
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    revenue = db.Column(db.Numeric(10, 2))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'type': self.type,
            'quantity': self.quantity,
            'price': float(self.price) if self.price else None,
            'revenue': float(self.revenue) if self.revenue else None,
            'date': self.date.isoformat() if self.date else None
        }

# Create tables
with app.app_context():
    try:
        db.create_all()
        print("✅ PostgreSQL connection successful!")
        print(f"📁 Database connected")
    except Exception as e:
        print(f"❌ Connection error: {e}")

CLEAR_HISTORY_PIN = os.environ.get('CLEAR_HISTORY_PIN', '4598')
CORS(app)

# ===== ROUTES =====
def validate_json(required_fields):
    if not request.is_json:
        return jsonify({'message': 'Request must be JSON'}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'message': 'Invalid or empty JSON body'}), 400

    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({'message': 'Missing fields', 'fields': missing}), 400

    return data

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products', methods=['POST'])
def add_product():
    validation = validate_json(['name', 'category', 'quantity', 'price'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    data['name'] = data['name'].strip()
    data['category'] = data['category'].strip()
    
    # Check if product exists
    existing = Product.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'message': 'Product already exists'}), 400

    # Create new product
    product = Product(
        name=data['name'],
        category=data['category'],
        quantity=data['quantity'],
        price=data['price']
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({'message': 'Product added', 'id': product.id}), 201

@app.route('/products', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sales/total', methods=['GET'])
def get_total_sales():
    try:
        transactions = Transaction.query.filter_by(type='sale').all()
        
        total_items = sum(t.quantity for t in transactions)
        total_revenue = sum(float(t.revenue or 0) for t in transactions)
        
        return jsonify({
            'totalItems': total_items,
            'totalRevenue': total_revenue,
            'saleCount': len(transactions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sales/download', methods=['GET'])
def download_sales():
    try:
        transactions = Transaction.query.filter_by(type='sale').order_by(Transaction.date).all()
        
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Sold Items'
        sheet.append(['Sale Date', 'Product ID', 'Product Name', 'Quantity', 'Unit Price', 'Revenue'])

        total_revenue = 0
        for t in transactions:
            product = Product.query.get(t.product_id)
            product_name = product.name if product else ''
            
            total_revenue += float(t.revenue or 0)
            
            sheet.append([
                t.date.strftime('%Y-%m-%d %H:%M:%S') if t.date else '',
                t.product_id,
                product_name,
                t.quantity,
                float(t.price or 0),
                float(t.revenue or 0)
            ])

        sheet.append([])
        sheet.append(['', '', '', '', 'Total Revenue', total_revenue])

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        return send_file(
            output,
            download_name='sold_items.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/clear', methods=['POST'])
def clear_history():
    validation = validate_json(['pin'])
    if isinstance(validation, tuple):
        return validation

    if validation.get('pin') != CLEAR_HISTORY_PIN:
        return jsonify({'message': 'Invalid PIN'}), 401

    Transaction.query.filter_by(type='sale').delete()
    db.session.commit()
    
    return jsonify({'message': 'Sales history cleared'}), 200

@app.route('/sell/<int:product_id>', methods=['POST'])
def sell_product(product_id):
    validation = validate_json(['quantity'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    quantity = data['quantity']
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404
        
    if product.quantity < quantity:
        return jsonify({'message': 'Insufficient quantity'}), 400

    product_price = float(product.price)
    revenue = quantity * product_price

    # Update product quantity
    product.quantity -= quantity
    
    # Create transaction
    transaction = Transaction(
        product_id=product_id,
        type='sale',
        quantity=quantity,
        price=product_price,
        revenue=revenue
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Product sold'}), 200

@app.route('/restock/<int:product_id>', methods=['POST'])
def restock_product(product_id):
    validation = validate_json(['quantity'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    quantity = data['quantity']
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    # Update product quantity
    product.quantity += quantity
    
    # Create transaction
    transaction = Transaction(
        product_id=product_id,
        type='restock',
        quantity=quantity
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Product restocked'}), 200

if __name__ == '__main__':
    app.run(debug=False)
