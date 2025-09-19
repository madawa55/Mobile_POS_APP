from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from functools import wraps
import uuid
import secrets
import hashlib
import barcode
from barcode.writer import ImageWriter
import io
import base64
from PIL import Image, ImageDraw, ImageFont

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
    role = db.Column(db.String(20), nullable=False)  # admin, owner, manager, cashier
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

class Feature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    is_enabled = db.Column(db.Boolean, default=False)
    requires_activation = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Association table for many-to-many relationship between ActivationKey and Feature
activation_key_features = db.Table('activation_key_features',
    db.Column('activation_key_id', db.Integer, db.ForeignKey('activation_key.id'), primary_key=True),
    db.Column('feature_id', db.Integer, db.ForeignKey('feature.id'), primary_key=True)
)

class ActivationKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(128), nullable=False, unique=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    feature_id = db.Column(db.Integer, db.ForeignKey('feature.id'), nullable=True)  # For backward compatibility
    bundle_name = db.Column(db.String(100))  # Name for the feature bundle
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship('Business', backref='activation_keys')
    feature = db.relationship('Feature', backref='activation_keys')  # Single feature (backward compatibility)
    features = db.relationship('Feature', secondary=activation_key_features,
                              backref=db.backref('bundle_keys', lazy='dynamic'))  # Multiple features

class BusinessFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    feature_id = db.Column(db.Integer, db.ForeignKey('feature.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    activated_at = db.Column(db.DateTime)
    activation_key_id = db.Column(db.Integer, db.ForeignKey('activation_key.id'))

    business = db.relationship('Business', backref='business_features')
    feature = db.relationship('Feature', backref='business_features')
    activation_key = db.relationship('ActivationKey', backref='business_feature')

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
    elif current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

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
    if not is_feature_active('view_inventory'):
        flash('Inventory viewing feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('dashboard'))

    products = Product.query.filter_by(business_id=current_user.business_id).all()
    categories = Category.query.filter_by(business_id=current_user.business_id).all()
    return render_template('manager/products.html', products=products, categories=categories)

@app.route('/products/add', methods=['GET', 'POST'])
@role_required(['manager', 'owner'])
def add_product():
    if not is_feature_active('add_product'):
        flash('Add product feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('product_management'))

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
    if not is_feature_active('stock_management'):
        flash('Stock management feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('dashboard'))

    products = Product.query.filter_by(business_id=current_user.business_id).all()
    return render_template('manager/inventory.html', products=products)

# Barcode Printing Routes
@app.route('/print-labels')
@role_required(['manager', 'owner'])
def print_labels():
    if not is_feature_active('barcode_scanner'):
        flash('Barcode printing feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('dashboard'))

    products = Product.query.filter_by(business_id=current_user.business_id, is_active=True).all()
    return render_template('manager/print_labels.html', products=products)

@app.route('/api/generate-barcode-label/<int:product_id>')
@role_required(['manager', 'owner'])
def generate_barcode_label(product_id):
    if not is_feature_active('barcode_scanner'):
        return jsonify({'success': False, 'message': 'Barcode printing feature not activated'})

    product = Product.query.filter_by(
        id=product_id,
        business_id=current_user.business_id
    ).first()

    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})

    try:
        # Generate barcode
        CODE128 = barcode.get_barcode_class('code128')
        barcode_instance = CODE128(product.barcode, writer=ImageWriter())

        # Create barcode image in memory
        barcode_buffer = io.BytesIO()
        barcode_instance.write(barcode_buffer)
        barcode_buffer.seek(0)

        # Create label with product info
        label_image = create_product_label(product, barcode_buffer)

        # Convert to base64 for response
        img_buffer = io.BytesIO()
        label_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'product_name': product.name,
            'barcode': product.barcode,
            'price': product.price,
            'profit_margin': ((product.price - product.cost) / product.cost * 100) if product.cost > 0 else 0
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating barcode: {str(e)}'})

@app.route('/api/bulk-generate-labels', methods=['POST'])
@role_required(['manager', 'owner'])
def bulk_generate_labels():
    if not is_feature_active('barcode_scanner'):
        return jsonify({'success': False, 'message': 'Barcode printing feature not activated'})

    data = request.json
    product_ids = data.get('product_ids', [])

    if not product_ids:
        return jsonify({'success': False, 'message': 'No products selected'})

    try:
        labels = []
        for product_id in product_ids:
            product = Product.query.filter_by(
                id=product_id,
                business_id=current_user.business_id
            ).first()

            if product:
                # Generate barcode
                CODE128 = barcode.get_barcode_class('code128')
                barcode_instance = CODE128(product.barcode, writer=ImageWriter())

                barcode_buffer = io.BytesIO()
                barcode_instance.write(barcode_buffer)
                barcode_buffer.seek(0)

                # Create label
                label_image = create_product_label(product, barcode_buffer)

                img_buffer = io.BytesIO()
                label_image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()

                labels.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'image': f'data:image/png;base64,{img_base64}',
                    'price': product.price,
                    'profit_margin': ((product.price - product.cost) / product.cost * 100) if product.cost > 0 else 0
                })

        return jsonify({'success': True, 'labels': labels})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating labels: {str(e)}'})

def create_product_label(product, barcode_buffer):
    """Create a product label with barcode, price, and product info"""
    # Load barcode image
    barcode_img = Image.open(barcode_buffer)

    # Create label dimensions (standard label size)
    label_width = 400
    label_height = 200

    # Create new image with white background
    label = Image.new('RGB', (label_width, label_height), 'white')
    draw = ImageDraw.Draw(label)

    try:
        # Try to use a system font, fallback to default if not available
        title_font = ImageFont.truetype("arial.ttf", 16)
        price_font = ImageFont.truetype("arial.ttf", 20)
        info_font = ImageFont.truetype("arial.ttf", 12)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        price_font = ImageFont.load_default()
        info_font = ImageFont.load_default()

    # Calculate profit
    profit_margin = ((product.price - product.cost) / product.cost * 100) if product.cost > 0 else 0
    profit_amount = product.price - product.cost

    # Resize barcode to fit label
    barcode_width = 280
    barcode_height = 80
    barcode_resized = barcode_img.resize((barcode_width, barcode_height))

    # Position barcode
    barcode_x = (label_width - barcode_width) // 2
    barcode_y = 50
    label.paste(barcode_resized, (barcode_x, barcode_y))

    # Add product name (truncate if too long)
    product_name = product.name[:30] + "..." if len(product.name) > 30 else product.name
    name_bbox = draw.textbbox((0, 0), product_name, font=title_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = (label_width - name_width) // 2
    draw.text((name_x, 10), product_name, fill='black', font=title_font)

    # Add price prominently
    price_text = f"${product.price:.2f}"
    price_bbox = draw.textbbox((0, 0), price_text, font=price_font)
    price_width = price_bbox[2] - price_bbox[0]
    price_x = (label_width - price_width) // 2
    draw.text((price_x, 140), price_text, fill='green', font=price_font)

    # Add profit information
    profit_text = f"Profit: ${profit_amount:.2f} ({profit_margin:.1f}%)"
    profit_bbox = draw.textbbox((0, 0), profit_text, font=info_font)
    profit_width = profit_bbox[2] - profit_bbox[0]
    profit_x = (label_width - profit_width) // 2
    draw.text((profit_x, 170), profit_text, fill='blue', font=info_font)

    # Add barcode number
    barcode_text = product.barcode
    barcode_text_bbox = draw.textbbox((0, 0), barcode_text, font=info_font)
    barcode_text_width = barcode_text_bbox[2] - barcode_text_bbox[0]
    barcode_text_x = (label_width - barcode_text_width) // 2
    draw.text((barcode_text_x, 32), barcode_text, fill='black', font=info_font)

    return label

# Owner Routes
@app.route('/owner')
@role_required(['owner'])
def owner_dashboard():
    if not is_feature_active('sales_reports'):
        flash('Sales reporting feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('dashboard'))

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
    if not is_feature_active('user_management'):
        flash('User management feature is not activated for your business. Contact your administrator.', 'error')
        return redirect(url_for('dashboard'))

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

@app.route('/api/candle-data')
@role_required(['manager', 'owner'])
def candle_data():
    timeframe = request.args.get('timeframe', '1d')  # 1m, 5m, 1d, 1month

    # Calculate data points based on timeframe
    if timeframe == '1m':
        # Last 60 minutes
        points = 60
        delta_unit = 'minute'
    elif timeframe == '5m':
        # Last 5 hours (60 five-minute intervals)
        points = 60
        delta_unit = 'minute'
        points *= 5
    elif timeframe == '1d':
        # Last 30 days
        points = 30
        delta_unit = 'day'
    elif timeframe == '1month':
        # Last 12 months
        points = 12
        delta_unit = 'month'
    else:
        points = 30
        delta_unit = 'day'

    data = []
    for i in range(points):
        if delta_unit == 'minute':
            date = datetime.utcnow() - timedelta(minutes=i)
            if timeframe == '5m':
                # Round to nearest 5-minute interval
                date = date.replace(minute=(date.minute // 5) * 5, second=0, microsecond=0)
        elif delta_unit == 'day':
            date = datetime.utcnow().date() - timedelta(days=i)
        else:  # month
            date = datetime.utcnow().replace(day=1) - timedelta(days=32 * i)
            date = date.replace(day=1)

        # Get transactions for this period
        if delta_unit == 'minute':
            if timeframe == '1m':
                start_time = date
                end_time = date + timedelta(minutes=1)
            else:  # 5m
                start_time = date
                end_time = date + timedelta(minutes=5)

            transactions = Transaction.query.filter(
                Transaction.business_id == current_user.business_id,
                Transaction.created_at >= start_time,
                Transaction.created_at < end_time
            ).all()
        elif delta_unit == 'day':
            transactions = Transaction.query.filter(
                Transaction.business_id == current_user.business_id,
                db.func.date(Transaction.created_at) == date
            ).all()
        else:  # month
            next_month = (date.replace(day=28) + timedelta(days=4)).replace(day=1)
            transactions = Transaction.query.filter(
                Transaction.business_id == current_user.business_id,
                Transaction.created_at >= date,
                Transaction.created_at < next_month
            ).all()

        # Calculate OHLC (Open, High, Low, Close) values
        amounts = [t.total_amount for t in transactions] if transactions else [0]

        if amounts and amounts != [0]:
            open_val = amounts[0]
            high_val = max(amounts)
            low_val = min(amounts)
            close_val = amounts[-1]
            volume = len(amounts)
        else:
            open_val = high_val = low_val = close_val = 0
            volume = 0

        timestamp = date.strftime('%Y-%m-%d %H:%M') if delta_unit == 'minute' else date.strftime('%Y-%m-%d')

        data.append({
            'timestamp': timestamp,
            'open': float(open_val),
            'high': float(high_val),
            'low': float(low_val),
            'close': float(close_val),
            'volume': volume
        })

    return jsonify(data[::-1])  # Reverse to show chronological order

@app.route('/api/forecast-data')
@role_required(['manager', 'owner'])
def forecast_data():
    timeframe = request.args.get('timeframe', '1d')

    # Get historical data for prediction
    historical_data = []

    if timeframe == '1m':
        # Use last 60 minutes to predict next minute
        for i in range(60):
            date = datetime.utcnow() - timedelta(minutes=i)
            transactions = Transaction.query.filter(
                Transaction.business_id == current_user.business_id,
                Transaction.created_at >= date,
                Transaction.created_at < date + timedelta(minutes=1)
            ).all()
            total = sum(t.total_amount for t in transactions) if transactions else 0
            historical_data.append(total)
    elif timeframe == '5m':
        # Use last 12 five-minute intervals to predict next 5 minutes
        for i in range(12):
            date = datetime.utcnow() - timedelta(minutes=i*5)
            date = date.replace(minute=(date.minute // 5) * 5, second=0, microsecond=0)
            transactions = Transaction.query.filter(
                Transaction.business_id == current_user.business_id,
                Transaction.created_at >= date,
                Transaction.created_at < date + timedelta(minutes=5)
            ).all()
            total = sum(t.total_amount for t in transactions) if transactions else 0
            historical_data.append(total)
    elif timeframe == '1d':
        # Use last 30 days to predict next day
        for i in range(30):
            date = datetime.utcnow().date() - timedelta(days=i)
            total = db.session.query(db.func.sum(Transaction.total_amount)).filter(
                Transaction.business_id == current_user.business_id,
                db.func.date(Transaction.created_at) == date
            ).scalar() or 0
            historical_data.append(float(total))
    else:  # 1month
        # Use last 12 months to predict next month
        for i in range(12):
            date = datetime.utcnow().replace(day=1) - timedelta(days=32 * i)
            date = date.replace(day=1)
            next_month = (date.replace(day=28) + timedelta(days=4)).replace(day=1)
            total = db.session.query(db.func.sum(Transaction.total_amount)).filter(
                Transaction.business_id == current_user.business_id,
                Transaction.created_at >= date,
                Transaction.created_at < next_month
            ).scalar() or 0
            historical_data.append(float(total))

    # Simple moving average prediction
    if len(historical_data) >= 3:
        forecast = sum(historical_data[:3]) / 3  # Average of last 3 periods
    else:
        forecast = historical_data[0] if historical_data else 0

    # Add some variation for realistic candlestick
    variation = forecast * 0.1  # 10% variation
    forecast_open = forecast
    forecast_high = forecast + variation
    forecast_low = forecast - variation if forecast > variation else 0
    forecast_close = forecast + (variation * 0.5)

    # Calculate next timestamp
    now = datetime.utcnow()
    if timeframe == '1m':
        next_time = now + timedelta(minutes=1)
        timestamp = next_time.strftime('%Y-%m-%d %H:%M')
    elif timeframe == '5m':
        next_time = now + timedelta(minutes=5)
        timestamp = next_time.strftime('%Y-%m-%d %H:%M')
    elif timeframe == '1d':
        next_time = now + timedelta(days=1)
        timestamp = next_time.strftime('%Y-%m-%d')
    else:  # 1month
        next_time = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        timestamp = next_time.strftime('%Y-%m-%d')

    return jsonify({
        'timestamp': timestamp,
        'open': float(forecast_open),
        'high': float(forecast_high),
        'low': float(forecast_low),
        'close': float(forecast_close),
        'volume': 0,
        'is_forecast': True
    })

# Admin Routes
@app.route('/admin')
@role_required(['admin'])
def admin_dashboard():
    total_businesses = Business.query.count()
    total_features = Feature.query.count()
    active_features = Feature.query.filter_by(is_enabled=True).count()
    total_keys = ActivationKey.query.count()
    used_keys = ActivationKey.query.filter_by(is_used=True).count()

    recent_activations = db.session.query(ActivationKey, Business, Feature).join(
        Business, ActivationKey.business_id == Business.id
    ).join(
        Feature, ActivationKey.feature_id == Feature.id
    ).filter(ActivationKey.is_used == True).order_by(
        ActivationKey.used_at.desc()
    ).limit(10).all()

    return render_template('admin/dashboard.html',
                         total_businesses=total_businesses,
                         total_features=total_features,
                         active_features=active_features,
                         total_keys=total_keys,
                         used_keys=used_keys,
                         recent_activations=recent_activations)

@app.route('/admin/features')
@role_required(['admin'])
def admin_features():
    features = Feature.query.all()
    return render_template('admin/features.html', features=features)

@app.route('/admin/features/add', methods=['GET', 'POST'])
@role_required(['admin'])
def add_feature():
    if request.method == 'POST':
        feature = Feature(
            name=request.form['name'],
            description=request.form['description'],
            is_enabled=bool(request.form.get('is_enabled')),
            requires_activation=bool(request.form.get('requires_activation'))
        )
        db.session.add(feature)
        db.session.commit()
        flash('Feature added successfully!', 'success')
        return redirect(url_for('admin_features'))

    return render_template('admin/add_feature.html')

@app.route('/admin/features/toggle/<int:feature_id>')
@role_required(['admin'])
def toggle_feature(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    feature.is_enabled = not feature.is_enabled
    db.session.commit()
    flash(f'Feature {feature.name} {"enabled" if feature.is_enabled else "disabled"}!', 'success')
    return redirect(url_for('admin_features'))

@app.route('/admin/activation-keys')
@role_required(['admin'])
def admin_activation_keys():
    keys = db.session.query(ActivationKey, Business, Feature).join(
        Business, ActivationKey.business_id == Business.id
    ).join(
        Feature, ActivationKey.feature_id == Feature.id
    ).order_by(ActivationKey.created_at.desc()).all()

    return render_template('admin/activation_keys.html', keys=keys)

@app.route('/admin/activation-keys/generate', methods=['GET', 'POST'])
@role_required(['admin'])
def generate_activation_key():
    if request.method == 'POST':
        business_id = request.form['business_id']
        expires_days = int(request.form.get('expires_days', 365))
        bundle_name = request.form.get('bundle_name', 'Feature Bundle')

        # Check if it's a single feature or bundle
        feature_ids = request.form.getlist('feature_ids')
        single_feature_id = request.form.get('feature_id')

        if single_feature_id:
            # Single feature (backward compatibility)
            feature_ids = [single_feature_id]

        if not feature_ids:
            flash('Please select at least one feature.', 'error')
            return redirect(url_for('generate_activation_key'))

        # Generate unique activation key
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        activation_key = ActivationKey(
            key_hash=key_hash,
            business_id=business_id,
            bundle_name=bundle_name if len(feature_ids) > 1 else None,
            expires_at=datetime.utcnow() + timedelta(days=expires_days)
        )

        # For backward compatibility, set feature_id if only one feature
        if len(feature_ids) == 1:
            activation_key.feature_id = int(feature_ids[0])

        db.session.add(activation_key)
        db.session.flush()  # Get the activation key ID

        # Add features to the bundle
        for feature_id in feature_ids:
            feature = Feature.query.get(int(feature_id))
            if feature:
                activation_key.features.append(feature)

        db.session.commit()

        feature_names = [Feature.query.get(int(fid)).name for fid in feature_ids]
        flash(f'Activation key generated: {raw_key}<br>Features: {", ".join(feature_names)}', 'success')
        return redirect(url_for('admin_activation_keys'))

    businesses = Business.query.all()
    features = Feature.query.filter_by(requires_activation=True).all()
    return render_template('admin/generate_key.html', businesses=businesses, features=features)

@app.route('/admin/businesses')
@role_required(['admin'])
def admin_businesses():
    businesses = Business.query.all()
    business_features = {}

    for business in businesses:
        business_features[business.id] = db.session.query(BusinessFeature, Feature).join(
            Feature, BusinessFeature.feature_id == Feature.id
        ).filter(BusinessFeature.business_id == business.id).all()

    return render_template('admin/businesses.html', businesses=businesses, business_features=business_features)

@app.route('/admin/business/<int:business_id>/features')
@role_required(['admin'])
def business_features_detail(business_id):
    business = Business.query.get_or_404(business_id)

    # Get all features and their activation status for this business
    all_features = Feature.query.all()
    feature_status = []

    for feature in all_features:
        business_feature = BusinessFeature.query.filter_by(
            business_id=business_id,
            feature_id=feature.id
        ).first()

        activation_key = None
        if business_feature and business_feature.activation_key_id:
            activation_key = ActivationKey.query.get(business_feature.activation_key_id)

        feature_status.append({
            'feature': feature,
            'business_feature': business_feature,
            'activation_key': activation_key,
            'is_active': business_feature.is_active if business_feature else False
        })

    # Get activation history
    activation_keys = ActivationKey.query.filter_by(
        business_id=business_id
    ).order_by(ActivationKey.created_at.desc()).all()

    return render_template('admin/business_features.html',
                         business=business,
                         feature_status=feature_status,
                         activation_keys=activation_keys)

# Feature activation route for business owners
@app.route('/activate-feature', methods=['GET', 'POST'])
@role_required(['owner'])
def activate_feature():
    if request.method == 'POST':
        activation_key = request.form['activation_key']
        key_hash = hashlib.sha256(activation_key.encode()).hexdigest()

        key_record = ActivationKey.query.filter_by(
            key_hash=key_hash,
            business_id=current_user.business_id,
            is_used=False
        ).first()

        if not key_record:
            flash('Invalid or already used activation key!', 'error')
            return redirect(url_for('activate_feature'))

        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            flash('Activation key has expired!', 'error')
            return redirect(url_for('activate_feature'))

        # Get features to activate (bundle or single)
        features_to_activate = []
        if key_record.features:
            # Bundle key
            features_to_activate = key_record.features
        elif key_record.feature_id:
            # Single feature (backward compatibility)
            features_to_activate = [key_record.feature]

        if not features_to_activate:
            flash('No features found for this activation key!', 'error')
            return redirect(url_for('activate_feature'))

        # Activate all features
        activated_features = []
        for feature in features_to_activate:
            business_feature = BusinessFeature.query.filter_by(
                business_id=current_user.business_id,
                feature_id=feature.id
            ).first()

            if business_feature:
                business_feature.is_active = True
                business_feature.activated_at = datetime.utcnow()
                business_feature.activation_key_id = key_record.id
            else:
                business_feature = BusinessFeature(
                    business_id=current_user.business_id,
                    feature_id=feature.id,
                    is_active=True,
                    activated_at=datetime.utcnow(),
                    activation_key_id=key_record.id
                )
                db.session.add(business_feature)

            activated_features.append(feature.name)

        # Mark key as used
        key_record.is_used = True
        key_record.used_at = datetime.utcnow()

        db.session.commit()

        if len(activated_features) == 1:
            flash(f'Feature "{activated_features[0]}" activated successfully!', 'success')
        else:
            bundle_name = key_record.bundle_name or "Feature Bundle"
            flash(f'{bundle_name} activated successfully!<br>Features: {", ".join(activated_features)}', 'success')

        return redirect(url_for('owner_dashboard'))

    available_features = Feature.query.filter_by(is_enabled=True, requires_activation=True).all()
    activated_features = db.session.query(BusinessFeature, Feature).join(
        Feature, BusinessFeature.feature_id == Feature.id
    ).filter(
        BusinessFeature.business_id == current_user.business_id,
        BusinessFeature.is_active == True
    ).all()

    return render_template('activate_feature.html',
                         available_features=available_features,
                         activated_features=activated_features)

# Helper function to check if a feature is active for current business
def is_feature_active(feature_name):
    if not current_user.is_authenticated:
        return False

    feature = Feature.query.filter_by(name=feature_name, is_enabled=True).first()
    if not feature:
        return False

    if not feature.requires_activation:
        return True

    business_feature = BusinessFeature.query.filter_by(
        business_id=current_user.business_id,
        feature_id=feature.id,
        is_active=True
    ).first()

    return business_feature is not None

# Make helper function available in templates
app.jinja_env.globals.update(is_feature_active=is_feature_active)

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
        {'username': 'admin', 'email': 'admin@demo.com', 'role': 'admin'},
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

    # Create demo features - Core POS Features
    features_data = [
        # Core POS Features (require activation)
        {'name': 'add_product', 'description': 'Add new products to inventory', 'is_enabled': True, 'requires_activation': True},
        {'name': 'edit_product', 'description': 'Edit existing product details', 'is_enabled': True, 'requires_activation': True},
        {'name': 'delete_product', 'description': 'Delete products from system', 'is_enabled': True, 'requires_activation': True},
        {'name': 'view_inventory', 'description': 'View inventory and stock levels', 'is_enabled': True, 'requires_activation': True},
        {'name': 'stock_management', 'description': 'Adjust stock quantities', 'is_enabled': True, 'requires_activation': True},
        {'name': 'sales_reports', 'description': 'View sales reports and analytics', 'is_enabled': True, 'requires_activation': True},
        {'name': 'transaction_history', 'description': 'View transaction history', 'is_enabled': True, 'requires_activation': True},
        {'name': 'user_management', 'description': 'Manage system users', 'is_enabled': True, 'requires_activation': True},
        {'name': 'pos_terminal', 'description': 'Point of sale terminal access', 'is_enabled': True, 'requires_activation': False},

        # Advanced Features
        {'name': 'advanced_reporting', 'description': 'Advanced analytics and reporting features', 'is_enabled': True, 'requires_activation': True},
        {'name': 'inventory_alerts', 'description': 'Low stock alerts and inventory management', 'is_enabled': True, 'requires_activation': True},
        {'name': 'multi_payment', 'description': 'Support for multiple payment methods', 'is_enabled': True, 'requires_activation': True},
        {'name': 'customer_loyalty', 'description': 'Customer loyalty and rewards program', 'is_enabled': False, 'requires_activation': True},
        {'name': 'barcode_scanner', 'description': 'Advanced barcode scanning capabilities', 'is_enabled': True, 'requires_activation': True},
    ]

    for feature_data in features_data:
        feature = Feature(
            name=feature_data['name'],
            description=feature_data['description'],
            is_enabled=feature_data['is_enabled'],
            requires_activation=feature_data['requires_activation']
        )
        db.session.add(feature)

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