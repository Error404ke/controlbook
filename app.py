from flask import Flask, Request, jsonify
from sympy import product
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson import ObjectId
import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/msfavour'
mongo = PyMongo(app)
CORS(app)

#add product
@app.route('/products', methods=['POST'])
def add_product():
    data = Request.json()
    product_id= mongo.db.products.insert_one({
        'name': data['name'],
        'cartegory': data['cartegory'],
        'quantity': data['quantity'],
        'price': data['price']
    }).inserted_id
    return jsonify({'id': str(product_id)}),
    if product_id:
        return jsonify({'message': 'Product already exists'})
    result = mongo.db.products.insert_one(product)
    return jsonify({'message': 'Product added', 'id': str(result.inserted_id)}), 201

# get all products
@app.route('/products', methods=['GET'])
def get_products():
    product= list(mongo.db.products.find())
    for p in product:
        p['_id'] = str(p['_id'])
    return jsonify(product)

#sell product
@app.route('/sell/<product_id>', methods=['POST'])
def sell_product(product_id):
    data= Request.json()
    quantity = data['quantity']
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if product and product['quantity'] >= quantity:
        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$inc': {'quantity': -quantity}})

        mongo.db.transactions.insert_one({
            'product_id': ObjectId(product_id),
            'type': 'sale',
            'quantity': quantity,
            'date': datetime.datetime.now()
        })
        return jsonify({'message': 'Product sold'}), 200
    else:
        return jsonify({'message': 'Insufficient quantity or product not found'}), 400
    
    #restock product
@app.route('/restock/<product_id>', methods=['POST'])
def restock_product(product_id):
    data = Request.json()
    quantity = data['quantity']
    mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$inc': {'quantity': quantity}})
    mongo.db.transactions.insert_one({
        'product_id': ObjectId(product_id),
        'type': 'restock',
        'quantity': quantity,
        'date': datetime.datetime.now()
    })
    return jsonify({'message': 'Product restocked'}), 200

if __name__ == '__main__':    app.run(debug=True)

    #     new_quantity = product['quantity'] - quantity
    #     mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': {'quantity': new_quantity}})
    #     sale_id = mongo.db.sales.insert_one({
    #         'product_id': ObjectId(product_id),
    #         'quantity': quantity,
    #         'date': datetime.datetime.now()
    #     }).inserted_id
    #     return jsonify({'message': 'Product sold', 'sale_id': str(sale_id)}), 200
    # else:
    #     return jsonify({'message': 'Insufficient quantity or product not found'}), 400