from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_graphql import GraphQLView
from graphene import ObjectType, String, Schema
from functools import wraps
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
CORS(app)
app.secret_key = "your_secret_key"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='KGS')  # Currency field for Kyrgyzstani Som
    photo_path = db.Column(db.String(255))
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
# Ensure that the database is created within the app context
with app.app_context():
    db.create_all()

@app.route('/view_products')
def view_products():
    with app.app_context():
        products = Product.query.all()
        product_list = [{'id': product.id, 'product_name': product.product_name, 'price': product.price, 'category': product.category,'photo_path': product.photo_path,'description': product.description} for product in products]
        return jsonify(product_list)
# Define the login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route for the home page or product view
@app.route('/') 
def products():
    with app.app_context():
        products = Product.query.all()
        return render_template('products.html', products=products)

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Check submitted credentials
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Example 'logout' endpoint
@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Route for the admin panel
@app.route('/admin')
@login_required
def admin():
    with app.app_context():
        products = Product.query.all()
        return render_template('admin.html', products=products)

# Route for changing prices in the admin panel
@app.route('/change_prices', methods=['POST'])
@login_required
def change_prices():
    with app.app_context():
        if request.method == 'POST':
            for product in Product.query.all():
                new_price = request.form.get('price_' + str(product.id))
                if new_price is not None and new_price != '':
                    product.price = float(new_price)
                    db.session.commit()

            return redirect(url_for('admin'))

# Route for adding a product in the admin panel
@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    with app.app_context():
        if request.method == 'POST':
            product_name = request.form['product_name']
            price = request.form['price']
            category = request.form['category']
            description = request.form['description']
            # Handling photo upload
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
            else:
                photo_path = None

            # Saving the product to the database
            new_product = Product(product_name=product_name, price=price, photo_path=filename, category=category,description=description)
            db.session.add(new_product)
            db.session.commit()

            return redirect(url_for('admin'))

# Route for deleting a product in the admin panel
@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    with app.app_context():
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()

    return redirect(url_for('admin'))

# GraphQL Configuration
class ProductType(ObjectType):
    name = String()
    price = String()

class Query(ObjectType):
    products = String()

    def resolve_products(self, info):
        with app.app_context():
            products = Product.query.all()
            return [{'name': p.product_name, 'price': p.price} for p in products]

schema = Schema(query=Query)
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)
