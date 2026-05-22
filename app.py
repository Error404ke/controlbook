import os

from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson import ObjectId
import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/msfavour'
CLEAR_HISTORY_PIN = os.environ.get('CLEAR_HISTORY_PIN', '4598')
mongo = PyMongo(app)
CORS(app)


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
    existing_product = mongo.db.products.find_one({'name': data['name']})
    if existing_product:
        return jsonify({'message': 'Product already exists'}), 400

    result = mongo.db.products.insert_one({
        'name': data['name'],
        'category': data['category'],
        'quantity': data['quantity'],
        'price': data['price']
    })

    return jsonify({'message': 'Product added', 'id': str(result.inserted_id)}), 201

# get all products
@app.route('/products', methods=['GET'])
def get_products():
    products = list(mongo.db.products.find())  # Fixed: variable name
    for p in products:
        p['_id'] = str(p['_id'])
    return jsonify(products)


@app.route('/sales/total', methods=['GET'])
def get_total_sales():
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


@app.route('/history/clear', methods=['POST'])
def clear_history():
    validation = validate_json(['pin'])
    if isinstance(validation, tuple):
        return validation

    if validation.get('pin') != CLEAR_HISTORY_PIN:
        return jsonify({'message': 'Invalid PIN'}), 401

    mongo.db.transactions.delete_many({})
    return jsonify({'message': 'Sales history cleared'}), 200


# sell product
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

# restock product
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
    app.run(debug=True)