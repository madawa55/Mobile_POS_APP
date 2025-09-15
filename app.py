from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from functools import wraps
import uuid

app = Flask(__name__)

# Production configuration with Railway environment variables
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production-' + str(uuid.uuid4()))

# Use PostgreSQL in production, SQLite for development
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Railway PostgreSQL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos_system.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Railway port configuration
PORT = int(os.environ.get('PORT', 5000))

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Database Models
class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='business', lazy=True)
    products = db.relationship('Product', backref='business', lazy=True)
    transactions = db.relationship('Transaction', backref='business', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # owner, manager, cashier
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, default=0)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    image_url = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')  # cash, card, digital
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='transactions')
    items = db.relationship('TransactionItem', backref='transaction', lazy=True, cascade='all, delete-orphan')

class TransactionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', backref='transaction_items')

# Database initialization for newer Flask versions
def init_db():
    """Initialize database - called at startup"""
    with app.app_context():
        try:
            db.create_all()

            # Initialize demo data if no businesses exist
            if Business.query.count() == 0:
                init_demo_data()
                print("Demo data initialized!")
        except Exception as e:
            print(f"Error initializing database: {e}")

# Initialize database on app creation (for newer Flask versions)
def create_tables():
    """Initialize database tables and demo data"""
    try:
        with app.app_context():
            db.create_all()

            # Initialize demo data if no businesses exist
            if Business.query.count() == 0:
                init_demo_data()
                print("Demo data initialized!")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Hook for first request (compatible with all Flask versions)
@app.before_request
def initialize_database():
    """Initialize database on first request"""
    if not hasattr(initialize_database, 'initialized'):
        try:
            db.create_all()
            # Initialize demo data if no businesses exist
            if Business.query.count() == 0:
                init_demo_data()
                print("Demo data initialized on first request!")
        except Exception as e:
            print(f"Error initializing database: {e}")

        # Mark as initialized to avoid running again
        initialize_database.initialized = True

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password) and user.is_active:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password) and user.is_active:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'cashier':
        return redirect(url_for('cashier_pos'))
    elif current_user.role == 'manager':
        return redirect(url_for('manager_dashboard'))
    elif current_user.role == 'owner':
        return redirect(url_for('owner_dashboard'))

    return render_template('dashboard.html')

# Cashier Routes
@app.route('/pos')
@role_required(['cashier', 'manager', 'owner'])
def cashier_pos():
    products = Product.query.filter_by(
        business_id=current_user.business_id,
        is_active=True
    ).all()
    categories = Category.query.filter_by(business_id=current_user.business_id).all()
    return render_template('cashier/pos.html', products=products, categories=categories)

@app.route('/api/barcode/<barcode>')
@role_required(['cashier', 'manager', 'owner'])
def get_product_by_barcode(barcode):
    product = Product.query.filter_by(
        barcode=barcode,
        business_id=current_user.business_id,
        is_active=True
    ).first()

    if product:
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'stock': product.stock_quantity,
                'image_url': product.image_url
            }
        })
    return jsonify({'success': False, 'message': 'Product not found'})

@app.route('/api/transaction', methods=['POST'])
@role_required(['cashier', 'manager', 'owner'])
def create_transaction():
    data = request.json

    try:
        # Create transaction
        transaction_id = str(uuid.uuid4())[:8].upper()
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=current_user.id,
            business_id=current_user.business_id,
            total_amount=data['total_amount'],
            payment_method=data.get('payment_method', 'cash')
        )
        db.session.add(transaction)
        db.session.flush()  # Get transaction ID

        # Add transaction items and update stock
        for item in data['items']:
            product = Product.query.get(item['product_id'])
            if product.stock_quantity < item['quantity']:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'Insufficient stock for {product.name}'
                })

            transaction_item = TransactionItem(
                transaction_id=transaction.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price']
            )
            db.session.add(transaction_item)

            # Update stock
            product.stock_quantity -= item['quantity']

        db.session.commit()
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Transaction completed successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Manager Routes
@app.route('/manager')
@role_required(['manager', 'owner'])
def manager_dashboard():
    # Get statistics
    total_products = Product.query.filter_by(business_id=current_user.business_id).count()
    low_stock_products = Product.query.filter(
        Product.business_id == current_user.business_id,
        Product.stock_quantity <= Product.min_stock_level
    ).count()

    today = datetime.utcnow().date()
    today_sales = db.session.query(db.func.sum(Transaction.total_amount)).filter(
        Transaction.business_id == current_user.business_id,
        db.func.date(Transaction.created_at) == today
    ).scalar() or 0

    recent_transactions = Transaction.query.filter_by(
        business_id=current_user.business_id
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    return render_template('manager/dashboard.html',
                         total_products=total_products,
                         low_stock_products=low_stock_products,
                         today_sales=today_sales,
                         recent_transactions=recent_transactions)

@app.route('/products')
@role_required(['manager', 'owner'])
def product_management():
    products = Product.query.filter_by(business_id=current_user.business_id).all()
    categories = Category.query.filter_by(business_id=current_user.business_id).all()
    return render_template('manager/products.html', products=products, categories=categories)

@app.route('/products/add', methods=['GET', 'POST'])
@role_required(['manager', 'owner'])
def add_product():
    if request.method == 'POST':
        # Handle file upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"uploads/{filename}"

        product = Product(
            name=request.form['name'],
            barcode=request.form['barcode'],
            price=float(request.form['price']),
            cost=float(request.form.get('cost', 0)),
            stock_quantity=int(request.form.get('stock_quantity', 0)),
            min_stock_level=int(request.form.get('min_stock_level', 5)),
            category_id=request.form.get('category_id') or None,
            business_id=current_user.business_id,
            image_url=image_url
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('product_management'))

    categories = Category.query.filter_by(business_id=current_user.business_id).all()
    return render_template('manager/add_product.html', categories=categories)

@app.route('/inventory')
@role_required(['manager', 'owner'])
def inventory():
    products = Product.query.filter_by(business_id=current_user.business_id).all()
    return render_template('manager/inventory.html', products=products)

# Owner Routes
@app.route('/owner')
@role_required(['owner'])
def owner_dashboard():
    # Get comprehensive statistics
    total_users = User.query.filter_by(business_id=current_user.business_id).count()
    total_products = Product.query.filter_by(business_id=current_user.business_id).count()

    # Sales statistics
    today = datetime.utcnow().date()
    today_sales = db.session.query(db.func.sum(Transaction.total_amount)).filter(
        Transaction.business_id == current_user.business_id,
        db.func.date(Transaction.created_at) == today
    ).scalar() or 0

    this_month = datetime.utcnow().replace(day=1).date()
    month_sales = db.session.query(db.func.sum(Transaction.total_amount)).filter(
        Transaction.business_id == current_user.business_id,
        db.func.date(Transaction.created_at) >= this_month
    ).scalar() or 0

    # Recent transactions
    recent_transactions = Transaction.query.filter_by(
        business_id=current_user.business_id
    ).order_by(Transaction.created_at.desc()).limit(20).all()

    return render_template('owner/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         today_sales=today_sales,
                         month_sales=month_sales,
                         recent_transactions=recent_transactions)

@app.route('/users')
@role_required(['owner'])
def user_management():
    users = User.query.filter_by(business_id=current_user.business_id).all()
    return render_template('owner/users.html', users=users)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/api/sales-data')
@role_required(['manager', 'owner'])
def sales_data():
    # Get last 7 days sales data
    data = []
    for i in range(7):
        date = datetime.utcnow().date() - timedelta(days=i)
        sales = db.session.query(db.func.sum(Transaction.total_amount)).filter(
            Transaction.business_id == current_user.business_id,
            db.func.date(Transaction.created_at) == date
        ).scalar() or 0
        data.append({'date': date.strftime('%Y-%m-%d'), 'sales': float(sales)})

    return jsonify(data)

def init_demo_data():
    """Initialize demo data for testing"""

    # Create demo business
    business = Business(
        name="Demo Store",
        address="123 Demo Street",
        phone="+1234567890",
        email="demo@store.com"
    )
    db.session.add(business)
    db.session.flush()

    # Create demo users
    users_data = [
        {'username': 'owner', 'email': 'owner@demo.com', 'role': 'owner'},
        {'username': 'manager', 'email': 'manager@demo.com', 'role': 'manager'},
        {'username': 'cashier', 'email': 'cashier@demo.com', 'role': 'cashier'},
    ]

    for user_data in users_data:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=generate_password_hash('password'),
            role=user_data['role'],
            business_id=business.id
        )
        db.session.add(user)

    # Create demo categories
    categories = ['Electronics', 'Food', 'Beverages', 'Clothing']
    category_objects = []
    for cat_name in categories:
        category = Category(name=cat_name, business_id=business.id)
        db.session.add(category)
        category_objects.append(category)

    db.session.flush()

    # Create demo products
    products_data = [
        {'name': 'Smartphone', 'barcode': '1234567890123', 'price': 299.99, 'stock': 50, 'category': 0},
        {'name': 'Laptop', 'barcode': '1234567890124', 'price': 599.99, 'stock': 25, 'category': 0},
        {'name': 'Bread', 'barcode': '1234567890125', 'price': 2.50, 'stock': 100, 'category': 1},
        {'name': 'Milk', 'barcode': '1234567890126', 'price': 3.99, 'stock': 75, 'category': 2},
        {'name': 'Coffee', 'barcode': '1234567890127', 'price': 12.99, 'stock': 30, 'category': 2},
        {'name': 'T-Shirt', 'barcode': '1234567890128', 'price': 19.99, 'stock': 40, 'category': 3},
    ]

    for prod_data in products_data:
        product = Product(
            name=prod_data['name'],
            barcode=prod_data['barcode'],
            price=prod_data['price'],
            cost=prod_data['price'] * 0.6,  # 40% margin
            stock_quantity=prod_data['stock'],
            min_stock_level=10,
            category_id=category_objects[prod_data['category']].id,
            business_id=business.id
        )
        db.session.add(product)

    db.session.commit()

# Initialize database when module is imported (for production)
try:
    init_db()
except:
    # If initialization fails, it will be retried on first request
    pass

if __name__ == '__main__':
    # For local development
    with app.app_context():
        db.create_all()

        # Initialize demo data if no businesses exist
        if Business.query.count() == 0:
            init_demo_data()
            print("Demo data initialized!")

    # Use environment PORT for Railway, debug=False in production
    debug_mode = os.environ.get('RAILWAY_ENVIRONMENT') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=PORT)