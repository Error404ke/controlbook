import os
from dotenv import load_dotenv
load_dotenv()
import logging
from flask import Flask, request, jsonify, render_template, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson import ObjectId
from openpyxl import Workbook
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/msfavour')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Get PIN from environment
CLEAR_HISTORY_PIN = os.environ.get('CLEAR_HISTORY_PIN', '4598')

# Initialize MongoDB
try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful!")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")

CORS(app)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    logger.error(f"Unhandled exception: {error}")
    return jsonify({'error': 'Something went wrong'}), 500

@app.route('/')
def home():
    return render_template('index.html')

def invalid_object_id(product_id):
    try:
        ObjectId(product_id)
        return False
    except Exception:
        return True

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

@app.route('/products', methods=['POST'])
def add_product():
    validation = validate_json(['name', 'category', 'quantity', 'price'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    
    # Clean data
    data['name'] = data['name'].strip()
    data['category'] = data['category'].strip()
    
    # Check if product exists (case-insensitive)
    existing_product = mongo.db.products.find_one({
        'name': {'$regex': f'^{data["name"]}$', '$options': 'i'}
    })
    
    if existing_product:
        return jsonify({'message': 'Product already exists'}), 400

    result = mongo.db.products.insert_one({
        'name': data['name'],
        'category': data['category'],
        'quantity': data['quantity'],
        'price': data['price']
    })

    return jsonify({'message': 'Product added', 'id': str(result.inserted_id)}), 201

@app.route('/products', methods=['GET'])
def get_products():
    try:
        products = list(mongo.db.products.find())
        for p in products:
            p['_id'] = str(p['_id'])
        return jsonify(products)
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        return jsonify({'error': 'Failed to fetch products'}), 500

@app.route('/sales/total', methods=['GET'])
def get_total_sales():
    try:
        pipeline = [
            {'$match': {'type': 'sale'}},
            {
                '$group': {
                    '_id': None,
                    'totalItems': {'$sum': '$quantity'},
                    'totalRevenue': {'$sum': '$revenue'},
                    'saleCount': {'$sum': 1}
                }
            }
        ]
        result = list(mongo.db.transactions.aggregate(pipeline))
        if not result:
            return jsonify({'totalItems': 0, 'totalRevenue': 0, 'saleCount': 0})

        totals = result[0]
        return jsonify({
            'totalItems': totals.get('totalItems', 0),
            'totalRevenue': totals.get('totalRevenue', 0),
            'saleCount': totals.get('saleCount', 0)
        })
    except Exception as e:
        logger.error(f"Error fetching sales summary: {e}")
        return jsonify({'error': 'Failed to fetch sales summary'}), 500

@app.route('/sales/download', methods=['GET'])
def download_sales():
    try:
        sales = list(mongo.db.transactions.find({'type': 'sale'}).sort('date', 1))

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Sold Items'
        sheet.append(['Sale Date', 'Product ID', 'Product Name', 'Quantity', 'Unit Price', 'Revenue'])

        total_revenue = 0
        for sale in sales:
            product_id = sale.get('product_id')
            product_name = ''
            if product_id:
                product = mongo.db.products.find_one({'_id': product_id})
                if product:
                    product_name = product.get('name', '')

            sale_date = sale.get('date')
            if isinstance(sale_date, datetime.datetime):
                sale_date = sale_date.strftime('%Y-%m-%d %H:%M:%S')

            quantity = sale.get('quantity', 0)
            price = sale.get('price', 0)
            revenue = sale.get('revenue', 0)
            total_revenue += revenue or 0

            sheet.append([
                sale_date,
                str(product_id) if product_id else '',
                product_name,
                quantity,
                price,
                revenue
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
        logger.error(f"Error downloading sales: {e}")
        return jsonify({'error': 'Failed to download sales'}), 500

@app.route('/history/clear', methods=['POST'])
def clear_history():
    validation = validate_json(['pin'])
    if isinstance(validation, tuple):
        return validation

    if validation.get('pin') != CLEAR_HISTORY_PIN:
        return jsonify({'message': 'Invalid PIN'}), 401

    mongo.db.transactions.delete_many({})
    return jsonify({'message': 'Sales history cleared'}), 200

@app.route('/sell/<product_id>', methods=['POST'])
def sell_product(product_id):
    if invalid_object_id(product_id):
        return jsonify({'message': 'Invalid product id'}), 400

    validation = validate_json(['quantity'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    quantity = data['quantity']
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})

    if not product:
        return jsonify({'message': 'Product not found'}), 404
    if product.get('quantity', 0) < quantity:
        return jsonify({'message': 'Insufficient quantity'}), 400

    product_price = product.get('price', 0)
    revenue = quantity * product_price

    mongo.db.products.update_one(
        {'_id': ObjectId(product_id)}, 
        {'$inc': {'quantity': -quantity}}
    )

    mongo.db.transactions.insert_one({
        'product_id': ObjectId(product_id),
        'type': 'sale',
        'quantity': quantity,
        'price': product_price,
        'revenue': revenue,
        'date': datetime.datetime.utcnow()
    })
    return jsonify({'message': 'Product sold'}), 200

@app.route('/restock/<product_id>', methods=['POST'])
def restock_product(product_id):
    if invalid_object_id(product_id):
        return jsonify({'message': 'Invalid product id'}), 400

    validation = validate_json(['quantity'])
    if isinstance(validation, tuple):
        return validation

    data = validation
    quantity = data['quantity']

    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    mongo.db.products.update_one(
        {'_id': ObjectId(product_id)}, 
        {'$inc': {'quantity': quantity}}
    )
    mongo.db.transactions.insert_one({
        'product_id': ObjectId(product_id),
        'type': 'restock',
        'quantity': quantity,
        'date': datetime.datetime.utcnow()
    })
    return jsonify({'message': 'Product restocked'}), 200

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False for production
