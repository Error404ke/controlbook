import os
import io
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from openpyxl import Workbook
import datetime
from dotenv import load_dotenv
from bcrypt import hashpw, gensalt, checkpw

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# PostgreSQL Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    DB_USER = os.environ.get('DB_USER', 'controlbook_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'John@4598')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'controlbook')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ===== USER MODEL =====
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

# ===== PRODUCT MODEL =====
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

# ===== TRANSACTION MODEL =====
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
        # Create default user if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default user created (username: admin, password: admin123)")
    except Exception as e:
        print(f"❌ Connection error: {e}")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

CLEAR_HISTORY_PIN = os.environ.get('CLEAR_HISTORY_PIN', '4598')
CORS(app)

# ===== AUTHENTICATION ROUTES =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ===== MAIN ROUTE =====
@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

# ===== PRODUCT ROUTES =====
@app.route('/products', methods=['POST'])
@login_required
def add_product():
    validation = validate_json(['name', 'category', 'quantity', 'price'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    data['name'] = data['name'].strip()
    data['category'] = data['category'].strip()
    
    # Check if product exists (no user_id filter)
    existing = Product.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'message': 'Product already exists'}), 400

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
@login_required
def get_products():
    try:
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sales/total', methods=['GET'])
@login_required
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
@login_required
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
@login_required
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
@login_required
def sell_product(product_id):
    try:
        validation = validate_json(['quantity'])
        if isinstance(validation, tuple):
            return validation

        data = validation
        quantity = data['quantity']
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404
            
        if product.quantity < quantity:
            return jsonify({'message': f'Insufficient quantity. Available: {product.quantity}'}), 400

        product_price = float(product.price)
        revenue = quantity * product_price

        product.quantity -= quantity
        
        transaction = Transaction(
            product_id=product_id,
            type='sale',
            quantity=quantity,
            price=product_price,
            revenue=revenue
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'message': f'Product sold: {quantity} units', 'id': product_id}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/restock/<int:product_id>', methods=['POST'])
@login_required
def restock_product(product_id):
    try:
        validation = validate_json(['quantity'])
        if isinstance(validation, tuple):
            return validation

        data = validation
        quantity = data['quantity']
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        product.quantity += quantity
        
        transaction = Transaction(
            product_id=product_id,
            type='restock',
            quantity=quantity
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'message': f'Product restocked: {quantity} units', 'id': product_id}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== HELPERS =====
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
@app.route('/admin/clear-products', methods=['POST'])
@login_required
def clear_products():
    try:
        # Delete all transactions first (foreign key constraint)
        Transaction.query.delete()
        Product.query.delete()
        db.session.commit()
        return jsonify({'message': 'All products cleared successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
