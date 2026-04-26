#!/usr/bin/env python3
"""
Freight Logistics Database Seeding Script
Creates sample data for testing and demonstration
"""

import mysql.connector
from datetime import datetime, timedelta
import random
import os

# Database connection
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "freight_logistics"),
}

def seed_database():
    """Populate database with sample data"""
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        print("🌱 Seeding Freight Logistics Database...")
        
        # 1. Create sample courier accounts
        print("\n📝 Creating courier accounts...")
        couriers = [
            ("juan_santos", "juan@courier.com", "Juan Santos", "09171234567"),
            ("maria_cruz", "maria@courier.com", "Maria Cruz", "09175555123"),
            ("pedro_garcia", "pedro@courier.com", "Pedro Garcia", "09176789012"),
            ("rosa_mendoza", "rosa@courier.com", "Rosa Mendoza", "09177778899"),
            ("carlos_reyes", "carlos@courier.com", "Carlos Reyes", "09178881234"),
        ]
        
        courier_ids = []
        for username, email, name, phone in couriers:
            try:
                # Using plaintext password for demo (already hashed admin account exists)
                cursor.execute("""
                    INSERT IGNORE INTO users (username, email, password_hash, role, full_name, phone, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                """, (username, email, "$2b$12$dummyhash", "courier", name, phone))
                courier_ids.append(cursor.lastrowid)
                print(f"  ✓ Created courier: {name}")
            except Exception as e:
                print(f"  ✗ Error creating courier {name}: {e}")
        
        conn.commit()
        
        # 2. Create sample shipments
        print("\n📦 Creating sample shipments...")
        shipment_data = [
            ("Juan Tan", "Makati CBD", "Cubao, Quezon City", "Electronics", "Regular", 2.5, 14.5741, 121.0193),
            ("Maria Gonzales", "Ayala Triangle", "Bonifacio Global City", "Documents", "Express", 0.5, 14.5521, 121.0569),
            ("Pedro Santos", "MOA Complex", "BGC, Taguig", "Fragile Items", "Critical", 1.2, 14.5529, 121.0038),
            ("Rosa Kim", "Quezon Avenue", "Makati Medical Center", "Medical Supplies", "Express", 3.0, 14.5816, 121.0196),
            ("Carlos Lopez", "SM Megamall", "Power Plant Mall", "Books", "Regular", 5.0, 14.5856, 121.0237),
            ("Ana Fernandez", "BGC", "Alabang", "Fashion Items", "Regular", 2.0, 14.6091, 121.0245),
            ("Miguel Torres", "Ermita", "Pasay City", "Food Items", "Express", 1.5, 14.5658, 121.0094),
            ("Sofia Ramirez", "Quiapo", "Intramuros", "Souvenir Items", "Regular", 0.8, 14.6019, 121.0044),
            ("Luis Martinez", "Escolta", "Binondo", "General Cargo", "Express", 4.2, 14.5946, 121.0081),
            ("Elena Garcia", "Taft Avenue", "Ermita", "Office Supplies", "Regular", 6.5, 14.5714, 121.0110),
        ]
        
        shipment_ids = []
        statuses = ["pending", "booking_confirmed", "picked_up", "in_transit", "delivered"]
        
        for customer, origin, dest, cargo, priority, weight, lat, lng in shipment_data:
            try:
                status = random.choice(statuses)
                cursor.execute("""
                    INSERT INTO shipments 
                    (tracking_code, customer_name, origin_address, destination_address, 
                     cargo_type, weight_kg, priority, status, current_step, 
                     last_lat, last_lng, expected_delivery)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    f"PH{datetime.now().strftime('%y%m%d')}{random.randint(10000, 99999)}",
                    customer, origin, dest, cargo, weight, priority, status,
                    random.randint(1, 7), lat, lng,
                    datetime.now() + timedelta(days=random.randint(1, 7))
                ))
                shipment_ids.append(cursor.lastrowid)
                print(f"  ✓ Created shipment: {customer} → {dest}")
            except Exception as e:
                print(f"  ✗ Error creating shipment: {e}")
        
        conn.commit()
        
        # 3. Create assignments
        print("\n🔗 Creating shipment assignments...")
        for shipment_id in shipment_ids[:len(courier_ids)]:
            try:
                courier_id = random.choice(courier_ids)
                cursor.execute("""
                    INSERT IGNORE INTO shipment_assignments 
                    (shipment_id, rider_id, assignment_notes)
                    VALUES (%s, %s, %s)
                """, (shipment_id, courier_id, f"Assigned on {datetime.now()}"))
                print(f"  ✓ Assigned shipment {shipment_id} to courier {courier_id}")
            except Exception as e:
                print(f"  ✗ Error assigning shipment: {e}")
        
        conn.commit()
        
        # 4. Create tracking updates
        print("\n📍 Creating tracking updates...")
        locations = [
            ("Booking Confirmed", "Warehouse", 14.5995, 120.9842),
            ("Picked Up", "Pickup Location", 14.5900, 120.9900),
            ("In Transit", "Along EDSA", 14.5800, 120.9800),
            ("At Hub", "Distribution Hub", 14.5700, 120.9900),
        ]
        
        for shipment_id in shipment_ids[:5]:
            try:
                for status, location, lat, lng in random.sample(locations, 2):
                    cursor.execute("""
                        INSERT INTO tracking_updates
                        (shipment_id, status, location_name, latitude, longitude, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (shipment_id, status, location, lat, lng, f"Status update at {datetime.now()}"))
                    print(f"  ✓ Added tracking update: {status}")
            except Exception as e:
                print(f"  ✗ Error creating tracking update: {e}")
        
        conn.commit()
        
        # 5. Create GPS tracking sessions and pings
        print("\n🛰️ Creating GPS tracking data...")
        for idx, shipment_id in enumerate(shipment_ids[:3]):
            try:
                # Create session
                cursor.execute("""
                    INSERT INTO gps_tracking_sessions
                    (shipment_id, is_active)
                    VALUES (%s, %s)
                """, (shipment_id, 1 if idx < 2 else 0))
                
                session_id = cursor.lastrowid
                
                # Add GPS pings
                base_lat = 14.5 + random.uniform(0, 0.5)
                base_lng = 120.9 + random.uniform(0, 0.5)
                
                for i in range(random.randint(3, 8)):
                    lat = base_lat + random.uniform(-0.01, 0.01)
                    lng = base_lng + random.uniform(-0.01, 0.01)
                    
                    cursor.execute("""
                        INSERT INTO gps_pings
                        (session_id, latitude, longitude, accuracy_meters, altitude)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (session_id, lat, lng, random.uniform(5, 20), random.uniform(0, 50)))
                
                print(f"  ✓ Created GPS session {session_id} with {random.randint(3, 8)} pings")
            except Exception as e:
                print(f"  ✗ Error creating GPS data: {e}")
        
        conn.commit()
        
        print("\n✅ Database seeding completed successfully!")
        print(f"  • {len(courier_ids)} courier accounts created")
        print(f"  • {len(shipment_ids)} sample shipments created")
        print(f"  • Shipment assignments and tracking data populated")
        print(f"  • Ready for demonstration and testing")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\nEnsure MySQL is running and the database 'freight_logistics' exists.")
        print("Run: mysql -u root -p < freight_logistics.sql")
        print("Run: mysql -u root -p freight_logistics < extended_schema.sql")

if __name__ == "__main__":
    seed_database()
