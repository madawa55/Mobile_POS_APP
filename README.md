# Multi-Business POS System

A comprehensive Point-of-Sale (POS) system built with Python Flask, designed for small businesses with multi-tenant support and mobile-responsive design.

## 🚀 Features

### Core Functionality
- **Multi-Business Support**: Each business has its own isolated data and users
- **Role-Based Access Control**: Owner, Manager, and Cashier roles with different permissions
- **Mobile-Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Inventory Management**: Automatic stock updates with low-stock alerts
- **Barcode Scanning Support**: Quick product lookup and sales processing
- **Receipt Printing**: Professional receipts with business branding
- **Comprehensive Reporting**: Sales analytics and business insights

### User Roles & Permissions

#### 👑 Owner
- Full system access
- User management (add/remove/edit users)
- Business settings and configuration
- Comprehensive transaction reporting
- Export data and generate reports
- Monitor all business activities

#### 🏢 Manager
- Product catalog management
- Inventory control and stock adjustments
- Sales reporting and analytics
- POS system access
- Monitor cashier activities

#### 💰 Cashier
- Point-of-sale operations
- Product scanning and sales processing
- Receipt printing
- Basic transaction handling

## 🛠️ Technology Stack

- **Backend**: Python 3.8+ with Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5, JavaScript (ES6+)
- **Authentication**: Flask-Login with session management
- **File Handling**: Werkzeug for secure file uploads
- **Charts**: Chart.js for analytics visualization

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone or download the project**
```bash
cd Mobile_POS_System
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize the database**
The application will automatically create the database and demo data on first run.

4. **Run the application**
```bash
python app.py
```

5. **Access the system**
Open your web browser and navigate to: `http://localhost:5000`

## 🔐 Default Demo Accounts

The system comes with pre-configured demo accounts:

| Username | Password | Role    | Description |
|----------|----------|---------|-------------|
| owner    | password | Owner   | Full system access |
| manager  | password | Manager | Product & inventory management |
| cashier  | password | Cashier | POS operations only |

**⚠️ Important**: Change these passwords in production!

## 🎯 Usage Guide

### Getting Started
1. Login with one of the demo accounts
2. Explore the dashboard based on your role
3. Add products through the Manager interface
4. Start processing sales through the POS interface

### Adding Products (Manager/Owner)
1. Navigate to "Products" → "Add New Product"
2. Fill in product details:
   - Name and barcode
   - Pricing information
   - Initial stock quantity
   - Product image (optional)
3. Save the product

### Processing Sales (All Roles)
1. Access the POS interface
2. Scan barcode or click on products to add to cart
3. Adjust quantities as needed
4. Select payment method (Cash/Card)
5. Complete transaction and print receipt

### Managing Inventory (Manager/Owner)
1. Go to "Inventory" section
2. View stock levels and filter products
3. Use quick adjustment tools for stock updates
4. Monitor low-stock alerts

## 📱 Mobile Support

The system is fully responsive and optimized for mobile devices:

- **Touch-friendly interface** for tablets and phones
- **Optimized product grid** for smaller screens
- **Mobile barcode scanning** support
- **Responsive navigation** that collapses on mobile
- **Touch gestures** for cart management

## 🎨 Customization

### Business Branding
- Update business information in the database
- Replace logo and colors in the CSS files
- Customize receipt template

### Adding Features
The modular architecture makes it easy to extend:
- Add new user roles
- Implement additional payment methods
- Integrate with external APIs
- Add more reporting features

## 📊 Database Schema

### Key Tables
- **Business**: Multi-tenant business information
- **User**: User accounts with role-based permissions
- **Product**: Product catalog with images and pricing
- **Transaction**: Sales transactions with line items
- **Category**: Product categorization

### Relationships
- Each business has multiple users, products, and transactions
- Products can belong to categories
- Transactions contain multiple line items
- Full referential integrity maintained

## 🔧 Configuration

### Environment Variables
Create a `.env` file for production settings:
```
SECRET_KEY=your-production-secret-key
DATABASE_URL=your-database-connection-string
DEBUG=False
```

### File Upload Settings
- Images are stored in `static/uploads/`
- Supported formats: JPG, PNG, GIF
- Maximum file size: 5MB (configurable)

## 🚀 Deployment

### Development
```bash
python app.py
# Runs on http://localhost:5000 with debug mode
```

### Production
1. Set environment variables
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Configure reverse proxy (Nginx, Apache)
4. Set up SSL certificates
5. Use a production database (PostgreSQL, MySQL)

### Example Production Setup
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📈 Performance Features

- **Efficient database queries** with proper indexing
- **Client-side caching** for product data
- **Lazy loading** for large product catalogs
- **Optimized images** with compression
- **Minimal JavaScript** for fast loading

## 🔒 Security Features

- **Role-based access control** (RBAC)
- **Session management** with secure cookies
- **CSRF protection** on all forms
- **SQL injection prevention** with ORM
- **File upload validation** and sanitization
- **Password hashing** with Werkzeug

## 🤝 Contributing

This is a complete business solution ready for deployment. To enhance the system:

1. Fork the repository
2. Create feature branches
3. Test thoroughly
4. Submit pull requests

## 📝 License

This project is available for business use. Please review the license terms before deployment.

## 🆘 Support & Troubleshooting

### Common Issues

**Database errors on startup:**
- Ensure proper permissions on the database file
- Check if SQLite is properly installed

**Image upload issues:**
- Verify `static/uploads/` directory exists and is writable
- Check file size limits in the configuration

**Mobile scanning not working:**
- Ensure HTTPS connection for camera access
- Test on different browsers and devices

### Getting Help

For technical support or feature requests:
1. Check the troubleshooting section
2. Review the code documentation
3. Test with the demo data first

## 🎯 Roadmap

Potential enhancements for future versions:
- **Multi-currency support**
- **Advanced reporting with PDF export**
- **Integration with accounting software**
- **Mobile app companion**
- **Cloud synchronization**
- **Advanced inventory features** (suppliers, purchase orders)
- **Customer loyalty programs**
- **Advanced analytics dashboard**

---

## 🏆 System Highlights

✅ **Production Ready**: Comprehensive error handling and validation
✅ **Scalable Architecture**: Easy to extend and customize
✅ **Mobile Optimized**: Perfect for tablet-based POS systems
✅ **Multi-Business**: Serve multiple clients with one deployment
✅ **Role-Based Security**: Proper access control for team management
✅ **Professional UI**: Modern, intuitive interface design
✅ **Comprehensive Features**: Everything needed for retail operations

This POS system is designed to help small businesses streamline their operations with a professional, feature-rich solution that grows with their needs.