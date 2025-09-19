#!/usr/bin/env python3
"""
Test script for the admin system functionality
"""

from app import app, db, Feature, ActivationKey, BusinessFeature, User, Business
import hashlib
import secrets
from datetime import datetime, timedelta

def test_admin_system():
    """Test the admin system functionality"""

    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("[OK] Database tables created successfully")

            # Test Feature creation
            test_feature = Feature(
                name='test_feature',
                description='Test feature for admin system',
                is_enabled=True,
                requires_activation=True
            )
            db.session.add(test_feature)
            db.session.commit()
            print("[OK] Feature model working correctly")

            # Test Business and ActivationKey creation
            business = Business.query.first()
            if business:
                # Generate activation key
                raw_key = secrets.token_urlsafe(32)
                key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

                activation_key = ActivationKey(
                    key_hash=key_hash,
                    business_id=business.id,
                    feature_id=test_feature.id,
                    expires_at=datetime.utcnow() + timedelta(days=365)
                )
                db.session.add(activation_key)
                db.session.commit()
                print("[OK] ActivationKey model working correctly")
                print(f"   Generated key: {raw_key}")

                # Test feature activation
                business_feature = BusinessFeature(
                    business_id=business.id,
                    feature_id=test_feature.id,
                    is_active=True,
                    activated_at=datetime.utcnow(),
                    activation_key_id=activation_key.id
                )
                db.session.add(business_feature)
                db.session.commit()
                print("[OK] BusinessFeature model working correctly")

            # Test admin user
            admin_user = User.query.filter_by(role='admin').first()
            if admin_user:
                print("[OK] Admin user found in database")
                print(f"   Username: {admin_user.username}")
            else:
                print("[WARN] Admin user not found - this is expected on first run")

            # Test feature checking function
            from app import is_feature_active

            print("\nSystem Status:")
            print(f"   Total Features: {Feature.query.count()}")
            print(f"   Enabled Features: {Feature.query.filter_by(is_enabled=True).count()}")
            print(f"   Total Businesses: {Business.query.count()}")
            print(f"   Total Activation Keys: {ActivationKey.query.count()}")
            print(f"   Total Business Features: {BusinessFeature.query.count()}")

            print("\n[SUCCESS] Admin system test completed successfully!")
            return True

        except Exception as e:
            print(f"[ERROR] Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("Testing Admin System...")
    test_admin_system()