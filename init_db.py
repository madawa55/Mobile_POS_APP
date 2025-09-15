#!/usr/bin/env python3
"""
Database initialization script for Railway deployment
Run this script to initialize the database with tables and demo data
"""

import os
import sys
from app import app, db, init_demo_data, Business

def initialize_database():
    """Initialize database tables and demo data"""
    print("Starting database initialization...")

    with app.app_context():
        try:
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")

            # Check if demo data already exists
            business_count = Business.query.count()
            print(f"Found {business_count} businesses in database")

            if business_count == 0:
                print("Initializing demo data...")
                init_demo_data()
                print("✅ Demo data initialized successfully!")

                # Verify initialization
                new_business_count = Business.query.count()
                print(f"✅ Created {new_business_count} business(es)")
            else:
                print("Demo data already exists, skipping initialization")

            print("\n🎉 Database initialization completed successfully!")
            print("\nDemo login credentials:")
            print("👑 Owner: username='owner', password='password'")
            print("🏢 Manager: username='manager', password='password'")
            print("💰 Cashier: username='cashier', password='password'")

        except Exception as e:
            print(f"❌ Error during database initialization: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    initialize_database()