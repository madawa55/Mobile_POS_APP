# Admin Control Panel & Feature Management System

## Overview

This system adds a comprehensive admin control panel with feature management and activation key functionality to your POS system. It allows administrators to control access to premium features and manage business-specific feature activation.

## System Architecture

### User Roles
- **Admin**: Super administrator with full system control
- **Owner**: Business owner with feature activation capabilities
- **Manager**: Business manager with standard management features
- **Cashier**: Point-of-sale operator with basic access

### Core Components

1. **Feature Management**: Control which features are available system-wide
2. **Activation Key System**: Secure key-based feature activation for businesses
3. **Business Feature Control**: Track and manage features per business
4. **Admin Dashboard**: Comprehensive control panel for system oversight

## Database Models

### Feature
- `name`: Unique feature identifier (e.g., 'advanced_reporting')
- `description`: Human-readable description
- `is_enabled`: Global feature toggle
- `requires_activation`: Whether feature needs activation key

### ActivationKey
- `key_hash`: Secure hash of the activation key
- `business_id`: Target business for activation
- `feature_id`: Feature to be activated
- `expires_at`: Optional expiration date
- `is_used`: Whether key has been used

### BusinessFeature
- `business_id`: Business that owns the feature
- `feature_id`: Activated feature
- `is_active`: Whether feature is currently active
- `activated_at`: Activation timestamp
- `activation_key_id`: Reference to the activation key used

## Admin Features

### 1. Feature Management (`/admin/features`)
- View all system features
- Enable/disable features globally
- Add new features
- Generate activation keys for specific features

### 2. Activation Key Management (`/admin/activation-keys`)
- View all generated keys
- Track key usage and expiration
- Generate new keys for businesses

### 3. Business Overview (`/admin/businesses`)
- View all registered businesses
- See which features each business has activated
- Generate activation keys for specific businesses

### 4. Admin Dashboard (`/admin`)
- System-wide statistics
- Recent activation activity
- Quick action buttons

## Business Owner Features

### Feature Activation (`/activate-feature`)
- View currently activated features
- Enter activation keys to unlock new features
- See available features for activation

## How It Works

### For Administrators:

1. **Create Features**: Add new features in the admin panel
2. **Enable Features**: Toggle features on/off system-wide
3. **Generate Keys**: Create activation keys for specific business-feature combinations
4. **Monitor Usage**: Track which businesses are using which features

### For Business Owners:

1. **Contact Admin**: Request activation key for desired feature
2. **Enter Key**: Use the activation interface to enter the provided key
3. **Activate Feature**: Key validation activates the feature immediately
4. **Use Feature**: Feature becomes available throughout the POS system

### For Developers:

Use the `is_feature_active()` helper function in templates:
```jinja2
{% if is_feature_active('advanced_reporting') %}
    <a href="#" class="btn btn-info">Export Report</a>
{% endif %}
```

## Security Features

- **Secure Key Generation**: Uses cryptographically secure random key generation
- **Hash Storage**: Only key hashes are stored in the database
- **Single-Use Keys**: Each activation key can only be used once
- **Business-Specific**: Keys are tied to specific businesses
- **Expiration Support**: Keys can have expiration dates
- **Role-Based Access**: Proper authorization for all admin functions

## Setup Instructions

### 1. Database Migration
The new models are automatically created when the application starts. No manual migration is needed.

### 2. Create Admin User
```python
from app import app, db, User, Business
from werkzeug.security import generate_password_hash

with app.app_context():
    # Find or create a business for the admin
    business = Business.query.first()
    if not business:
        business = Business(name="Admin Business", email="admin@example.com")
        db.session.add(business)
        db.session.commit()

    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('your_admin_password'),
        role='admin',
        business_id=business.id
    )
    db.session.add(admin)
    db.session.commit()
```

### 3. Initialize Sample Features
Sample features are automatically created in the demo data. You can add more through the admin interface.

## Default Features

The system comes with these sample features:

1. **advanced_reporting**: Advanced analytics and reporting
2. **inventory_alerts**: Low stock alerts and inventory management
3. **multi_payment**: Support for multiple payment methods
4. **customer_loyalty**: Customer loyalty and rewards program
5. **barcode_scanner**: Advanced barcode scanning capabilities

## API Endpoints

### Admin Routes (Require 'admin' role)
- `GET/POST /admin/features/add` - Add new feature
- `GET /admin/features/toggle/<id>` - Toggle feature on/off
- `GET/POST /admin/activation-keys/generate` - Generate activation key
- `GET /admin/activation-keys` - View all keys
- `GET /admin/businesses` - View all businesses

### Business Owner Routes (Require 'owner' role)
- `GET/POST /activate-feature` - Feature activation interface

## Usage Examples

### Adding a New Feature (Admin)
1. Navigate to `/admin/features`
2. Click "Add Feature"
3. Enter feature name (e.g., `customer_analytics`)
4. Add description
5. Choose if activation key is required
6. Save the feature

### Generating Activation Key (Admin)
1. Navigate to `/admin/activation-keys`
2. Click "Generate Key"
3. Select target business
4. Select feature to activate
5. Set expiration (optional)
6. Generate key and share with business owner

### Activating Feature (Business Owner)
1. Navigate to `/activate-feature`
2. Enter activation key provided by admin
3. Click "Activate Feature"
4. Feature becomes immediately available

## Testing

Run the test script to verify the system works correctly:
```bash
python test_admin_system.py
```

## Future Enhancements

- **Feature Usage Analytics**: Track how often features are used
- **Bulk Key Generation**: Generate multiple keys at once
- **Feature Dependencies**: Set up feature prerequisites
- **Time-Limited Features**: Features that expire after a certain period
- **Feature Groups**: Bundle related features together
- **API Key Management**: Allow feature access via API keys
- **Audit Logging**: Track all admin actions and feature usage

## Troubleshooting

### Key Validation Fails
- Check if key has expired
- Verify key is for the correct business
- Ensure feature is enabled globally
- Check if key has already been used

### Feature Not Showing
- Verify feature is enabled in admin panel
- Check if business has activated the feature
- Ensure user has proper role permissions
- Verify feature exists in database

### Admin Access Issues
- Confirm user has 'admin' role
- Check if admin routes are properly configured
- Verify database connection is working

## Support

For technical support or feature requests, please refer to the main application documentation or contact the development team.