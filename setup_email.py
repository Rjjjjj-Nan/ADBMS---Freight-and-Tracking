#!/usr/bin/env python3
"""
Script to add email functionality to the Freight & Logistics application.
Run this once to set up email confirmation features.
"""

import os

# Read the current app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Flask-Mail import (if not already present)
if 'from flask_mail import' not in content:
    old_import = 'from dotenv import load_dotenv'
    new_import = 'from dotenv import load_dotenv\nfrom flask_mail import Mail, Message'
    content = content.replace(old_import, new_import)
    print("✓ Added Flask-Mail import")

# 2. Add Flask-Mail configuration (after app.secret_key line)
if 'app.config[\'MAIL_SERVER\']' not in content:
    old_config = "app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')"
    new_config = """app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@freight-logistics.com')

mail = Mail(app)"""
    content = content.replace(old_config, new_config)
    print("✓ Added Flask-Mail configuration")

# 3. Add email sending function (before routes section)
email_function = '''
def send_booking_confirmation_email(user_email, user_name, parcel):
    """Send booking confirmation email with parcel details"""
    if not user_email:
        print("No email address provided, skipping email")
        return False
    
    try:
        subject = f"Booking Confirmation - Tracking #{parcel['tracking_number']}"
        
        body = f"""Dear {user_name},

Thank you for booking with Freight & Logistics! Your parcel has been successfully registered.

========== BOOKING DETAILS ==========
Tracking Number: {parcel['tracking_number']}
Status: {parcel['status'].replace('_', ' ').title()}

SENDER INFORMATION:
Name: {parcel['sender_name']}
Phone: {parcel['sender_phone']}
Address: {parcel['sender_address']}

RECEIVER INFORMATION:
Name: {parcel['receiver_name']}
Phone: {parcel['receiver_phone']}
Address: {parcel['receiver_address']}

SHIPMENT DETAILS:
From: {parcel['origin_city']}
To: {parcel['destination_city']}
Weight: {parcel['weight_kg']} kg
Shipping Method: {parcel['shipping_method'].replace('_', ' ').title()}
Cost: PHP {parcel['cost_php']:.2f}

BOOKING DATE: {parcel['created_at'].strftime('%B %d, %Y at %I:%M %p')}

=====================================

You can track your parcel anytime at:
http://127.0.0.1:5000/user/parcel/{parcel['parcel_id']}

For inquiries or issues:
Email: info@freight.com
Phone: (02) 8911-1888

Best regards,
Freight & Logistics Team"""
        
        msg = Message(subject=subject, recipients=[user_email], body=body)
        mail.send(msg)
        print(f"✓ Confirmation email sent to {user_email}")
        return True
    except Exception as e:
        print(f"⚠ Error sending confirmation email: {e}")
        return False
'''

if 'def send_booking_confirmation_email' not in content:
    # Add before the routes section
    routes_marker = '# ==================== ROUTES =='
    content = content.replace(routes_marker, email_function + '\n' + routes_marker)
    print("✓ Added email sending function")

# 4. Update the book_parcel route to send email
if 'send_booking_confirmation_email' not in content:
    old_book_section = '''            conn.commit()
            parcel_id = cursor.lastrowid
            
            # If courier selected, assign immediately'''
    
    new_book_section = '''            conn.commit()
            parcel_id = cursor.lastrowid
            
            # Fetch complete parcel details for email
            cursor.execute("""
                SELECT * FROM parcels WHERE parcel_id = %s
            """, (parcel_id,))
            parcel_details = cursor.fetchone()
            
            # Send confirmation email
            send_booking_confirmation_email(user_info['email'] if 'email' in user_info else user_info.get('email'), user_info['full_name'], parcel_details)
            
            # If courier selected, assign immediately'''
    
    content = content.replace(old_book_section, new_book_section)
    print("✓ Updated book_parcel route to send emails")
    
    # Also update the flash messages to mention email
    old_flash1 = "flash(f'Parcel booked successfully! Tracking #: {tracking_number}', 'success')"
    new_flash1 = "flash(f'Parcel booked successfully! Tracking #: {tracking_number}. Confirmation email sent.', 'success')"
    content = content.replace(old_flash1, new_flash1)
    
    old_flash2 = "flash(f'Parcel created! Please select a courier to complete the booking. Tracking #: {tracking_number}', 'warning')"
    new_flash2 = "flash(f'Parcel created! Confirmation email sent. Please select a courier to complete the booking. Tracking #: {tracking_number}', 'warning')"
    content = content.replace(old_flash2, new_flash2)
    print("✓ Updated flash messages")

# Write back to app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Email setup complete!")
print("\nNext steps:")
print("1. Update your .env file with:")
print("   MAIL_SERVER=smtp.gmail.com")
print("   MAIL_PORT=587")
print("   MAIL_USE_TLS=True")
print("   MAIL_USERNAME=your-email@gmail.com")
print("   MAIL_PASSWORD=your-app-password")
print("   MAIL_DEFAULT_SENDER=noreply@freight-logistics.com")
print("\n2. Run: pip install -r requirements.txt")
print("3. Restart your Flask application")
