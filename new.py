from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, ValidationError
from werkzeug.security import generate_password_hash
from sqlalchemy import Enum
from enum import Enum as PyEnum  # Importing Enum from the enum module
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration for SQLAlchemy to connect to the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:panda1234@localhost/ecommerce_db_2'
db = SQLAlchemy(app)
ma = Marshmallow(app)


class CustomerSchema(ma.Schema):
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone_number = fields.String(required=True)

    class Meta:
        fields = ("name", "email", "phone_number", "id")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)


class CustomerAccountSchema(ma.Schema):
    class Meta:
        fields = ("id", "username", "customer")

    customer = ma.Nested(CustomerSchema)  # Nesting CustomerSchema to include customer details

customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)


class ProductSchema(ma.Schema):
    name = fields.String(required=True)
    price = fields.Float(required=True)  # Changed to fields.Float

    class Meta:
        fields = ("name", "price", "id")

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# Customer Model
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone_number = db.Column(db.String(15))
    orders = db.relationship('Order', backref='customer')


# CustomerAccount Model
class CustomerAccount(db.Model):
    __tablename__ = 'customer_accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship('Customer', backref='customer_accounts', uselist=False)


# Association table for many-to-many relationship between Order and Product
order_product = db.Table('order_product',
    db.Column('order_id', db.Integer, db.ForeignKey('orders.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True)
)

# Product Model
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    orders = db.relationship('Order', secondary=order_product, backref=db.backref('products'))


# OrderStatus Enum
class OrderStatus(PyEnum):  # Using PyEnum for SQLAlchemy compatibility
    PENDING = "Pending"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELED = "Canceled"


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    status = db.Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    expected_delivery_date = db.Column(db.DateTime)  # Nullable; can be set after shipping
    products = db.relationship('Product', secondary=order_product, backref=db.backref('orders'))


# Customer routes
@app.route('/customers', methods=['GET'])  
def get_customers():
    customers = Customer.query.all()
    return customers_schema.jsonify(customers)

@app.route('/customers', methods=['POST'])  
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], phone_number=customer_data['phone_number'])
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "new customer added"}), 201  # Changed to 201 Created

@app.route('/customers/<int:id>', methods=['PUT'])  
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.phone_number = customer_data['phone_number']
    db.session.commit()
    return jsonify({"message": "updated customer"}), 200

@app.route('/customers/<int:id>', methods=['DELETE'])  
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": f"Customer with ID {id} deleted successfully!"}), 200


# Product routes
@app.route('/products', methods=['GET'])  
def get_products():
    products = Product.query.all()
    return products_schema.jsonify(products)

@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get_or_404(id)
    return product_schema.jsonify(product), 200

@app.route('/products/<int:id>', methods=['DELETE']) 
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"Product with ID {id} deleted successfully!"}), 200

@app.route('/products', methods=['POST'])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    new_product = Product(name=product_data['name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()
    return product_schema.jsonify(new_product), 201

@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    product.name = product_data['name']
    product.price = product_data['price']
    db.session.commit()
    return product_schema.jsonify(product), 200


# CustomerAccount route to get account details by ID
@app.route('/customer_accounts/<int:id>', methods=['GET'])
def get_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    return customer_account_schema.jsonify(customer_account), 200

@app.route('/customer_accounts', methods=['POST'])
def create_customer_account():
    data = request.json
    if 'username' not in data or 'password' not in data or 'customer_id' not in data:
        return jsonify({"error": "Missing required fields: 'username', 'password', 'customer_id'"}), 400
    customer = Customer.query.get(data['customer_id'])
    if not customer:
        return jsonify({"error": "Customer with provided ID does not exist"}), 404
    if CustomerAccount.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 409
    hashed_password = generate_password_hash(data['password'])
    new_account = CustomerAccount(
        username=data['username'],
        password=hashed_password,
        customer_id=data['customer_id']
    )
    db.session.add(new_account)
    db.session.commit()
    return customer_account_schema.jsonify(new_account), 201

@app.route('/customer_accounts/<int:id>', methods=['PUT'])
def update_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    data = request.json
    if 'username' in data:
        if CustomerAccount.query.filter(CustomerAccount.username == data['username'], CustomerAccount.id != id).first():
            return jsonify({"error": "Username already exists"}), 409
        customer_account.username = data['username']
    if 'password' in data:
        hashed_password = generate_password_hash(data['password'])
        customer_account.password = hashed_password
    db.session.commit()
    return customer_account_schema.jsonify(customer_account), 200

@app.route('/customer_accounts/<int:id>', methods=['DELETE'])
def delete_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    db.session.delete(customer_account)
    db.session.commit()
    return jsonify({"message": f"Customer account with ID {id} deleted successfully!"}), 200


@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = request.json
        customer_id = order_data['customer_id']
        product_ids = order_data['product_ids']
        
        new_order = Order(customer_id=customer_id)
        new_order.expected_delivery_date = datetime.utcnow() + timedelta(days=5)
        
        db.session.add(new_order)
        db.session.commit()

        for product_id in product_ids:
            product = Product.query.get(product_id)
            if product:
                new_order.products.append(product)
            else:
                return jsonify({"error": f"Product with ID {product_id} does not exist."}), 404

        db.session.commit()
        return jsonify({"message": "Order created successfully!", "order_id": new_order.id}), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

@app.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    order = Order.query.get_or_404(id)
    return jsonify({
        "id": order.id,
        "date": order.date,
        "customer_id": order.customer_id,
        "status": order.status,
        "expected_delivery_date": order.expected_delivery_date,
        "products": [product.id for product in order.products]
    }), 200




if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(debug=True)  # Run the Flask app
