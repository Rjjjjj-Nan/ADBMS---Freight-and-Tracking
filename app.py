import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
import bcrypt
from dotenv import load_dotenv
from flask_mail import Mail, Message

load_dotenv()

# Flask App Configuration
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@freight-logistics.com')

mail = Mail(app)

# MySQL Configuration
mysql_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'freight_logistics'),
    'autocommit': True
}

def get_db_connection():
    """Create a new database connection"""
    try:
        conn = mysql.connector.connect(**mysql_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def log_action(user_id, action, entity_type=None, entity_id=None, old_values=None, new_values=None):
    """Log user actions to audit_logs table"""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        ip_address = request.remote_addr if request else '127.0.0.1'
        user_agent = request.headers.get('User-Agent', '') if request else ''
        
        old_vals = json.dumps(old_values) if old_values else None
        new_vals = json.dumps(new_values) if new_values else None
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, action, entity_type, entity_id, old_vals, new_vals, ip_address, user_agent))
        conn.commit()
    except Error as e:
        print(f"Error logging action: {e}")
    finally:
        cursor.close()
        conn.close()

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

def verify_password(password, hash_val):
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hash_val.encode('utf-8'))

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.', 'danger')
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT role FROM users WHERE user_id = %s", (session['user_id'],))
            user = cursor.fetchone()
            if not user or user['role'] != 'admin':
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
        finally:
            cursor.close()
            conn.close()
        
        return f(*args, **kwargs)
    return decorated_function

def require_courier(f):
    """Decorator to require courier role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.', 'danger')
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT role FROM users WHERE user_id = %s", (session['user_id'],))
            user = cursor.fetchone()
            if not user or user['role'] != 'courier':
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
        finally:
            cursor.close()
            conn.close()
        
        return f(*args, **kwargs)
    return decorated_function

def require_user(f):
    """Decorator to require user (customer) role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.', 'danger')
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT role FROM users WHERE user_id = %s", (session['user_id'],))
            user = cursor.fetchone()
            if not user or user['role'] != 'user':
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
        finally:
            cursor.close()
            conn.close()
        
        return f(*args, **kwargs)
    return decorated_function


def send_booking_confirmation_email(user_email, user_name, parcel):
    """Send booking confirmation email with parcel details"""
    if not user_email:
        print("No email address provided, skipping email")
        return False
    
    try:
        status_text = parcel['status'].replace('_', ' ').title()
        shipping_method_text = parcel['shipping_method'].replace('_', ' ').title()
        booking_date_text = parcel['created_at'].strftime('%B %d, %Y at %I:%M %p')
        tracking_url = f"http://127.0.0.1:5000/user/parcel/{parcel['parcel_id']}"
        subject = f"Booking Confirmation - Tracking #{parcel['tracking_number']}"

        body = f"""Dear {user_name},

Your booking has been confirmed. Please find your receipt below.

Booking receipt
Tracking Number: {parcel['tracking_number']}
Status: {status_text}
Booking Date: {booking_date_text}

Sender
Name: {parcel['sender_name']}
Phone: {parcel['sender_phone']}
Address: {parcel['sender_address']}

Receiver
Name: {parcel['receiver_name']}
Phone: {parcel['receiver_phone']}
Address: {parcel['receiver_address']}

Shipment
From: {parcel['origin_city']}
To: {parcel['destination_city']}
Weight: {parcel['weight_kg']} kg
Shipping Method: {shipping_method_text}
Cost: PHP {parcel['cost_php']:.2f}

Track your parcel: {tracking_url}

For inquiries: info@freight.com | (02) 8911-1888

Freight & Logistics Team"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <div style="max-width:680px;margin:0 auto;padding:24px;">
        <div style="background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#fff;border-radius:18px 18px 0 0;padding:28px 30px;box-shadow:0 10px 30px rgba(15,23,42,.18);">
            <div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;opacity:.85;">Freight & Logistics</div>
            <div style="font-size:28px;font-weight:700;margin-top:8px;">Booking Receipt</div>
            <div style="font-size:14px;opacity:.9;margin-top:8px;">Your parcel booking is confirmed.</div>
        </div>

        <div style="background:#ffffff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 18px 18px;overflow:hidden;box-shadow:0 10px 30px rgba(15,23,42,.08);">
            <div style="padding:24px 30px 18px;border-bottom:1px dashed #d1d5db;">
                <div style="font-size:15px;margin-bottom:10px;">Dear {user_name},</div>
                <div style="font-size:14px;line-height:1.6;color:#4b5563;">Thank you for booking with Freight & Logistics. Below is your receipt-style summary for easy reference.</div>
            </div>

            <div style="padding:22px 30px;border-bottom:1px dashed #d1d5db;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;">Tracking Number</div>
                    <div style="font-size:20px;font-weight:700;color:#111827;">#{parcel['tracking_number']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;">Status</div>
                    <div style="display:inline-block;margin-top:6px;background:#dcfce7;color:#166534;padding:8px 14px;border-radius:999px;font-weight:700;font-size:13px;">{status_text}</div>
                </div>
            </div>

            <div style="padding:22px 30px;border-bottom:1px dashed #d1d5db;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                    <tr>
                        <td style="width:50%;vertical-align:top;padding-right:10px;">
                            <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;margin-bottom:8px;">Sender</div>
                            <div style="font-size:14px;line-height:1.7;color:#111827;">
                                <strong>{parcel['sender_name']}</strong><br>
                                {parcel['sender_phone']}<br>
                                {parcel['sender_address']}
                            </div>
                        </td>
                        <td style="width:50%;vertical-align:top;padding-left:10px;">
                            <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;margin-bottom:8px;">Receiver</div>
                            <div style="font-size:14px;line-height:1.7;color:#111827;">
                                <strong>{parcel['receiver_name']}</strong><br>
                                {parcel['receiver_phone']}<br>
                                {parcel['receiver_address']}
                            </div>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="padding:22px 30px;border-bottom:1px dashed #d1d5db;">
                <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;margin-bottom:12px;">Shipment Details</div>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;">From</td>
                        <td style="padding:8px 0;text-align:right;font-weight:600;color:#111827;">{parcel['origin_city']}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;">To</td>
                        <td style="padding:8px 0;text-align:right;font-weight:600;color:#111827;">{parcel['destination_city']}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;">Weight</td>
                        <td style="padding:8px 0;text-align:right;font-weight:600;color:#111827;">{parcel['weight_kg']} kg</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;">Shipping Method</td>
                        <td style="padding:8px 0;text-align:right;font-weight:600;color:#111827;">{shipping_method_text}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;">Booking Date</td>
                        <td style="padding:8px 0;text-align:right;font-weight:600;color:#111827;">{booking_date_text}</td>
                    </tr>
                </table>
            </div>

            <div style="padding:22px 30px;background:#f9fafb;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#6b7280;">Total Cost</div>
                    <div style="font-size:26px;font-weight:800;color:#0f172a;">PHP {parcel['cost_php']:.2f}</div>
                </div>
                <a href="{tracking_url}" style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700;font-size:14px;">Track Parcel</a>
            </div>

            <div style="padding:20px 30px;font-size:13px;line-height:1.7;color:#6b7280;">
                For inquiries: <strong>info@freight.com</strong> | <strong>(02) 8911-1888</strong><br>
                Freight & Logistics Team
            </div>
        </div>
    </div>
</body>
</html>
"""

        msg = Message(subject=subject, recipients=[user_email], body=body, html=html)
        mail.send(msg)
        print(f"✓ Confirmation email sent to {user_email}")
        return True
    except Exception as e:
        print(f"⚠ Error sending confirmation email: {e}")
        return False

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Landing page / Home"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.', 'danger')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT user_id, username, password_hash, role, full_name FROM users WHERE username = %s AND role = %s AND is_active = TRUE",
                (username, role)
            )
            user = cursor.fetchone()
            
            if user and verify_password(password, user['password_hash']):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name'] or user['username']
                
                log_action(user['user_id'], f'Login as {role}')
                
                if role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif role == 'courier':
                    return redirect(url_for('courier_dashboard'))
                else:  # user role
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid username, password, or role.', 'danger')
        except Error as e:
            print(f"Login error: {e}")
            flash('An error occurred during login.', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration route"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Get role from form, default to 'user' (customer)
        role = request.form.get('role', 'user')
        if not role:
            role = 'user'  # Fallback to user if empty
        role = role.lower().strip()
        
        # Validation
        if not username or not email or not password or len(password) < 8:
            flash('All fields required. Password must be at least 8 characters.', 'danger')
            return redirect(url_for('register'))
        
        if role not in ['user', 'courier']:
            flash('Invalid role selected. Please select Customer or Courier.', 'danger')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.', 'danger')
            return redirect(url_for('register'))
        
        cursor = conn.cursor()
        try:
            password_hash = hash_password(password)
            
            # Ensure role is always set
            print(f"DEBUG: Registering {username} with role='{role}'")
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, phone, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, password_hash, full_name, phone, role))
            conn.commit()
            
            print(f"DEBUG: User {username} registered successfully with role='{role}'")
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('Username or email already exists.', 'danger')
            else:
                print(f"Registration error: {e}")
                flash('An error occurred during registration.', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout route"""
    user_id = session.get('user_id')
    if user_id:
        log_action(user_id, 'Logout')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/user/profile', methods=['GET', 'POST'])
@require_user
def user_profile():
    """View and update the logged-in customer's profile"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('user_dashboard'))

    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            email = request.form.get('email', '').strip()

            if not full_name or not email:
                flash('Full name and email are required.', 'danger')
                return redirect(url_for('user_profile'))

            cursor.execute("""
                SELECT user_id, username, email, full_name, phone, address
                FROM users
                WHERE user_id = %s
            """, (session['user_id'],))
            old_user = cursor.fetchone()

            cursor.execute("""
                UPDATE users
                SET full_name = %s,
                    phone = %s,
                    address = %s,
                    email = %s
                WHERE user_id = %s
            """, (full_name, phone, address, email, session['user_id']))
            conn.commit()

            session['full_name'] = full_name
            log_action(
                session['user_id'],
                'Update Profile',
                'user',
                session['user_id'],
                old_values=old_user,
                new_values={'full_name': full_name, 'phone': phone, 'address': address, 'email': email}
            )

            flash('Profile updated successfully.', 'success')
            return redirect(url_for('user_profile'))

        cursor.execute("""
            SELECT user_id, username, email, full_name, phone, address, created_at
            FROM users
            WHERE user_id = %s
        """, (session['user_id'],))
        user = cursor.fetchone()

        if not user:
            flash('Profile not found.', 'danger')
            return redirect(url_for('user_dashboard'))

        return render_template('user_profile_edit.html', user=user)
    except Error as e:
        print(f"Error updating profile: {e}")
        flash('Error loading your profile.', 'danger')
        return redirect(url_for('user_dashboard'))
    finally:
        cursor.close()
        conn.close()

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@require_admin
def admin_dashboard():
    """Admin dashboard with analytics"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('index'))
    
    stats = {}
    daily_trend = []
    courier_performance = []
    destinations = []
    
    try:
        # Get delivery statistics
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetDeliveryStatistics')
        for result in cursor.stored_results():
            stats = result.fetchone()
        cursor.close()
        
        # Get daily trend
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetDailyDeliveryTrend')
        for result in cursor.stored_results():
            daily_trend = result.fetchall()
        cursor.close()
        
        # Get courier performance
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetCourierPerformance')
        for result in cursor.stored_results():
            courier_performance = result.fetchall()
        cursor.close()
        
        # Get parcels by destination
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetParcelsByDestination')
        for result in cursor.stored_results():
            destinations = result.fetchall()
        cursor.close()

        # Compute additional summary metrics not returned by stored proc
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                COUNT(*) AS total_parcels,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS total_delivered,
                COALESCE(ROUND(AVG(DATEDIFF(updated_at, created_at)), 1), 0) AS avg_delivery_time_days,
                COALESCE(ROUND(AVG(cost_php), 2), 0) AS avg_cost
            FROM parcels
            WHERE is_deleted = FALSE
        """)
        summary = cursor.fetchone()
        cursor.close()

        if summary:
            # Preserve existing stats keys when available, otherwise set them
            stats.setdefault('total_parcels', summary.get('total_parcels') or 0)
            stats.setdefault('delivered', summary.get('total_delivered') or 0)
            stats['avg_delivery_time_days'] = summary.get('avg_delivery_time_days') or 0
            stats['avg_cost'] = summary.get('avg_cost') or 0
            total_parcels = summary.get('total_parcels') or 0
            total_delivered = summary.get('total_delivered') or 0
            stats['success_rate_percent'] = round((total_delivered / total_parcels * 100), 1) if total_parcels > 0 else 0
        
    except Error as e:
        print(f"Error fetching analytics: {e}")
    finally:
        conn.close()
    
    return render_template('admin_dashboard.html', stats=stats, daily_trend=daily_trend, 
                         courier_performance=courier_performance, destinations=destinations)

@app.route('/admin/parcels')
@require_admin
def admin_parcels():
    """Admin parcels list"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    status_filter = request.args.get('status', '')
    destination_filter = request.args.get('destination', '')
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Build query
        query = "SELECT p.*, u.full_name as courier_name FROM parcels p LEFT JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id LEFT JOIN users u ON pa.courier_id = u.user_id WHERE p.is_deleted = FALSE"
        params = []
        
        if status_filter:
            query += " AND p.status = %s"
            params.append(status_filter)
        
        if destination_filter:
            query += " AND p.destination_city LIKE %s"
            params.append(f"%{destination_filter}%")
        
        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM ({query}) as subquery"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # Get paginated results
        offset = (page - 1) * per_page
        query += f" ORDER BY p.created_at DESC LIMIT {per_page} OFFSET {offset}"
        cursor.execute(query, params)
        parcels = cursor.fetchall()
        
        # Get couriers for assignment
        cursor.execute("SELECT user_id, full_name FROM users WHERE role = 'courier' AND is_active = TRUE")
        couriers = cursor.fetchall()
        
    except Error as e:
        print(f"Error fetching parcels: {e}")
        parcels = []
        total = 0
        couriers = []
    finally:
        cursor.close()
        conn.close()
    
    total_pages = (total + per_page - 1) // per_page
    return render_template('admin_parcels.html', parcels=parcels, couriers=couriers, 
                         page=page, total_pages=total_pages, status_filter=status_filter,
                         destination_filter=destination_filter)

@app.route('/admin/parcel/<int:parcel_id>/edit', methods=['GET', 'POST'])
@require_admin
def edit_parcel(parcel_id):
    """Edit parcel"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_parcels'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            destination = request.form.get('destination_city')
            cost = request.form.get('cost_php')
            status = request.form.get('status')
            notes = request.form.get('notes')
            
            # Get old values for audit
            cursor.execute("SELECT destination_city, cost_php, status, notes FROM parcels WHERE parcel_id = %s", (parcel_id,))
            old_parcel = cursor.fetchone()
            
            cursor.execute("""
                UPDATE parcels 
                SET destination_city = %s, cost_php = %s, status = %s, notes = %s, updated_at = NOW()
                WHERE parcel_id = %s
            """, (destination, cost, status, notes, parcel_id))
            conn.commit()
            
            # Log the action
            log_action(session['user_id'], 'Edit Parcel', 'parcel', parcel_id,
                      old_values=old_parcel, new_values={'destination_city': destination, 'cost_php': cost, 'status': status})
            
            flash('Parcel updated successfully.', 'success')
            return redirect(url_for('admin_parcels'))
        
        # GET request - fetch parcel data
        cursor.execute("SELECT * FROM parcels WHERE parcel_id = %s", (parcel_id,))
        parcel = cursor.fetchone()
        
    except Error as e:
        print(f"Error editing parcel: {e}")
        flash('An error occurred.', 'danger')
        return redirect(url_for('admin_parcels'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin_parcel_edit.html', parcel=parcel)

@app.route('/admin/parcel/<int:parcel_id>/delete', methods=['POST'])
@require_admin
def delete_parcel(parcel_id):
    """Soft delete parcel"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE parcels SET is_deleted = TRUE WHERE parcel_id = %s", (parcel_id,))
        conn.commit()
        log_action(session['user_id'], 'Delete Parcel', 'parcel', parcel_id)
        return jsonify({'success': True})
    except Error as e:
        print(f"Error deleting parcel: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/assign-parcel', methods=['POST'])
@require_admin
def assign_parcel():
    """Assign parcel to courier"""
    data = request.get_json()
    parcel_ids = data.get('parcel_ids', [])
    courier_id = data.get('courier_id')
    
    if not parcel_ids or not courier_id:
        return jsonify({'error': 'Missing data'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    try:
        for parcel_id in parcel_ids:
            cursor.execute("""
                INSERT INTO parcel_assignments (parcel_id, courier_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE assigned_at = NOW()
            """, (parcel_id, courier_id))
        conn.commit()
        
        log_action(session['user_id'], 'Assign Parcels', 'parcel_assignment', None,
                  new_values={'parcel_ids': parcel_ids, 'courier_id': courier_id})
        
        return jsonify({'success': True})
    except Error as e:
        print(f"Error assigning parcels: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

# ==================== COURIER ROUTES ====================

@app.route('/courier/dashboard')
@require_courier
def courier_dashboard():
    """Courier dashboard - shows only parcels assigned to the logged-in courier"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('index'))
    
    parcels = []
    status_counts = {'pending': 0, 'in_transit': 0, 'delivered': 0}
    
    try:
        user_id = session.get('user_id')
        
        # Validate user_id exists
        if not user_id:
            print("ERROR: user_id not found in session")
            flash('Session error. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        # Get assigned parcels for this courier using direct SQL query
        # This ensures we only fetch parcels assigned to this specific courier
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.parcel_id, p.tracking_number, p.sender_name, p.receiver_name,
                   p.origin_city, p.destination_city, p.weight_kg, p.cost_php,
                   p.status, p.shipping_method, p.created_at, p.updated_at
            FROM parcels p
            INNER JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
            WHERE pa.courier_id = %s AND p.is_deleted = FALSE
            ORDER BY p.created_at DESC
        """, (user_id,))
        parcels = cursor.fetchall()
        
        print(f"DEBUG: Courier {user_id} fetched {len(parcels)} assigned parcels")
        
        # Get last condition for each parcel
        if parcels:
            for parcel in parcels:
                cursor.execute("""
                    SELECT new_condition FROM parcel_conditions 
                    WHERE parcel_id = %s 
                    ORDER BY updated_at DESC LIMIT 1
                """, (parcel['parcel_id'],))
                condition_row = cursor.fetchone()
                parcel['last_condition'] = condition_row['new_condition'] if condition_row else None
        
        cursor.close()
        
        # Count by status
        for parcel in parcels:
            if parcel['status'] in status_counts:
                status_counts[parcel['status']] += 1
        
    except Error as e:
        print(f"Error fetching courier parcels: {e}")
        flash('Error fetching your parcels.', 'danger')
        parcels = []
        status_counts = {'pending': 0, 'in_transit': 0, 'delivered': 0}
    finally:
        conn.close()
    
    return render_template('courier_dashboard.html', parcels=parcels, status_counts=status_counts)

@app.route('/courier/parcel/<int:parcel_id>')
@require_courier
def courier_parcel_detail(parcel_id):
    """Courier parcel detail"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('courier_dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if parcel is assigned to this courier
        cursor.execute("""
            SELECT p.* FROM parcels p
            INNER JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
            WHERE p.parcel_id = %s AND pa.courier_id = %s
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()
        
        if not parcel:
            flash('Parcel not found or not assigned to you.', 'danger')
            return redirect(url_for('courier_dashboard'))
        
        # Get condition history
        cursor.execute("""
            SELECT * FROM parcel_conditions WHERE parcel_id = %s ORDER BY updated_at DESC
        """, (parcel_id,))
        conditions = cursor.fetchall()
        
    except Error as e:
        print(f"Error fetching parcel detail: {e}")
        flash('An error occurred.', 'danger')
        return redirect(url_for('courier_dashboard'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('courier_parcel_detail.html', parcel=parcel, conditions=conditions)

@app.route('/courier/parcel/<int:parcel_id>/update-condition', methods=['POST'])
@require_courier
def update_condition(parcel_id):
    """Update parcel condition"""
    new_condition = request.form.get('condition', '').strip()
    notes = request.form.get('notes', '').strip()
    
    # Validate condition is provided
    if not new_condition:
        flash('Please select a condition status.', 'danger')
        return redirect(url_for('courier_parcel_detail', parcel_id=parcel_id))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('courier_dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if parcel is assigned to this courier
        cursor.execute("""
            SELECT status FROM parcels p
            INNER JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
            WHERE p.parcel_id = %s AND pa.courier_id = %s
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()
        
        if not parcel:
            flash('Parcel not found or not assigned to you.', 'danger')
            return redirect(url_for('courier_dashboard'))
        
        # Insert condition record - only columns that exist in the actual table
        cursor.execute("""
            INSERT INTO parcel_conditions (parcel_id, new_condition, notes)
            VALUES (%s, %s, %s)
        """, (parcel_id, new_condition, notes if notes else None))
        
        # Update parcel status based on condition
        status_mapping = {
            'delivered': 'delivered',
            'in_transit': 'in_transit',
            'returned': 'returned',
            'intact': 'in_transit',
            'damaged': 'in_transit',
            'delayed': 'in_transit',
            'lost': 'returned'
        }
        
        new_status = status_mapping.get(new_condition, parcel['status'])
        if new_status != parcel['status']:
            cursor.execute("""
                UPDATE parcels SET status = %s, updated_at = NOW() WHERE parcel_id = %s
            """, (new_status, parcel_id))
        
        conn.commit()
        log_action(session['user_id'], 'Update Parcel Condition', 'parcel_condition', parcel_id,
                  new_values={'condition': new_condition, 'notes': notes})
        
        flash('Condition updated successfully.', 'success')
    except Error as e:
        print(f"Error updating condition: {e}")
        conn.rollback()
        flash(f'Error updating condition: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('courier_parcel_detail', parcel_id=parcel_id))

# ==================== USER (CUSTOMER) ROUTES ====================

def generate_tracking_number():
    """Generate a unique tracking number"""
    import string
    import random
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TRK{timestamp}{random_suffix}"

@app.route('/user/dashboard')
@require_user
def user_dashboard():
    """User dashboard - shows parcels booked by the logged-in user"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('index'))
    
    parcels = []
    status_counts = {'pending': 0, 'in_transit': 0, 'delivered': 0, 'cancelled': 0}
    
    try:
        user_id = session.get('user_id')
        cursor = conn.cursor(dictionary=True)
        
        # Get user's parcels
        cursor.execute("""
            SELECT p.* FROM parcels p
            WHERE p.user_id = %s AND p.is_deleted = FALSE
            ORDER BY p.created_at DESC
        """, (user_id,))
        parcels = cursor.fetchall()
        
        # Get courier assignment info for each parcel
        for parcel in parcels:
            cursor.execute("""
                SELECT pa.assignment_id, u.user_id as courier_id, u.full_name as courier_name, u.phone as courier_phone
                FROM parcel_assignments pa
                LEFT JOIN users u ON pa.courier_id = u.user_id
                WHERE pa.parcel_id = %s
                ORDER BY pa.assigned_at DESC LIMIT 1
            """, (parcel['parcel_id'],))
            assignment = cursor.fetchone()
            parcel['courier_id'] = assignment['courier_id'] if assignment else None
            parcel['courier_name'] = assignment['courier_name'] if assignment else 'Unassigned'
            parcel['courier_phone'] = assignment['courier_phone'] if assignment else None
            
            # Count by status
            if parcel['status'] in status_counts:
                status_counts[parcel['status']] += 1
        
        cursor.close()
    except Error as e:
        print(f"Error fetching user parcels: {e}")
        flash('Error fetching your parcels.', 'danger')
    finally:
        conn.close()
    
    return render_template('user_dashboard.html', parcels=parcels, status_counts=status_counts)

@app.route('/user/book-parcel', methods=['GET', 'POST'])
@require_user
def book_parcel():
    """Book a new courier for parcel delivery"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            receiver_name = request.form.get('receiver_name')
            receiver_phone = request.form.get('receiver_phone')
            receiver_address = request.form.get('receiver_address')
            destination_city = request.form.get('destination_city')
            origin_city = request.form.get('origin_city')
            weight_kg = request.form.get('weight_kg', 0)
            shipping_method = request.form.get('shipping_method', 'standard')
            courier_id = request.form.get('courier_id')
            scheduled_time = request.form.get('scheduled_pickup_time')
            notes = request.form.get('notes')
            
            # Validation
            if not all([receiver_name, receiver_phone, receiver_address, destination_city, origin_city]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('book_parcel'))
            
            # Pricing logic
            pricing = {'standard': 100, 'express': 200, 'super': 300, 'international': 500}
            base_cost = pricing.get(shipping_method, 100)
            weight_surcharge = float(weight_kg or 0) * 10  # ₱10 per kg
            cost_php = base_cost + weight_surcharge
            
            # Get user info for sender
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT full_name, phone, address FROM users WHERE user_id = %s
            """, (session['user_id'],))
            user_info = cursor.fetchone()
            
            # Generate tracking number
            tracking_number = generate_tracking_number()
            
            # Insert parcel
            cursor.execute("""
                INSERT INTO parcels (
                    tracking_number, user_id, sender_name, sender_phone, sender_address,
                    receiver_name, receiver_phone, receiver_address, origin_city, 
                    destination_city, weight_kg, cost_php, shipping_method, 
                    scheduled_pickup_time, notes, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                tracking_number, session['user_id'], 
                user_info['full_name'], user_info['phone'], user_info['address'],
                receiver_name, receiver_phone, receiver_address,
                origin_city, destination_city, weight_kg, cost_php, 
                shipping_method, scheduled_time if scheduled_time else None, notes
            ))
            conn.commit()
            parcel_id = cursor.lastrowid
            
            # Fetch complete parcel details for email
            cursor.execute("""
                SELECT parcel_id, tracking_number, user_id, sender_name, sender_phone, sender_address,
                       receiver_name, receiver_phone, receiver_address, origin_city, destination_city,
                       weight_kg, cost_php, shipping_method, notes, status, created_at
                FROM parcels WHERE parcel_id = %s
            """, (parcel_id,))
            parcel_details = cursor.fetchone()
            
            # Fetch user email for confirmation email
            cursor.execute("SELECT email, full_name FROM users WHERE user_id = %s", (session['user_id'],))
            user_info = cursor.fetchone()
            
            # If courier selected, assign immediately
            if courier_id:
                cursor.execute("""
                    INSERT INTO parcel_assignments (parcel_id, courier_id)
                    VALUES (%s, %s)
                """, (parcel_id, courier_id))
                conn.commit()
                log_action(session['user_id'], 'Book Parcel with Courier Assignment', 'parcel', parcel_id,
                          new_values={'courier_id': courier_id, 'tracking': tracking_number})
                flash(f'Parcel booked successfully! Tracking #: {tracking_number}', 'success')
            else:
                log_action(session['user_id'], 'Book Parcel - Pending Courier Assignment', 'parcel', parcel_id,
                          new_values={'tracking': tracking_number})
                flash(f'Parcel created! Please select a courier to complete the booking. Tracking #: {tracking_number}', 'warning')
            
            # Send confirmation email
            if parcel_details and user_info:
                send_booking_confirmation_email(user_info['email'], user_info['full_name'], parcel_details)
                flash('Confirmation email sent to your registered email address.', 'info')
            
            cursor.close()
            return redirect(url_for('user_dashboard'))
            
        except Error as e:
            print(f"Error booking parcel: {e}")
            flash('Error creating parcel booking.', 'danger')
    
    # GET request - show booking form with available couriers
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get user info to pre-fill sender details
        cursor.execute("""
            SELECT full_name, phone, address FROM users WHERE user_id = %s
        """, (session['user_id'],))
        user_info = cursor.fetchone()
        
        # Get available couriers with ratings
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.phone,
                   COUNT(cr.rating_id) as rating_count,
                   ROUND(AVG(cr.rating_stars), 2) as avg_rating
            FROM users u
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE u.role = 'courier' AND u.is_active = TRUE
            GROUP BY u.user_id, u.full_name, u.phone
            ORDER BY avg_rating DESC, u.full_name ASC
        """)
        couriers = cursor.fetchall()
        cursor.close()
        
        return render_template('user_book_parcel.html', user_info=user_info, couriers=couriers)
    except Error as e:
        print(f"Error loading booking form: {e}")
        flash('Error loading booking form.', 'danger')
        return redirect(url_for('user_dashboard'))
    finally:
        conn.close()

@app.route('/user/parcel/<int:parcel_id>')
@require_user
def user_parcel_detail(parcel_id):
    """View parcel details and contact courier"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('user_dashboard'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get parcel - verify it belongs to the user
        cursor.execute("""
            SELECT * FROM parcels WHERE parcel_id = %s AND user_id = %s AND is_deleted = FALSE
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()
        
        if not parcel:
            flash('Parcel not found.', 'danger')
            return redirect(url_for('user_dashboard'))
        
        # Get assigned courier
        cursor.execute("""
            SELECT pa.assignment_id, u.user_id, u.full_name, u.phone, u.email,
                   COUNT(cr.rating_id) as rating_count,
                   ROUND(AVG(cr.rating_stars), 2) as avg_rating
            FROM parcel_assignments pa
            LEFT JOIN users u ON pa.courier_id = u.user_id
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE pa.parcel_id = %s
            GROUP BY pa.assignment_id, u.user_id, u.full_name, u.phone, u.email
            ORDER BY pa.assigned_at DESC LIMIT 1
        """, (parcel_id,))
        courier = cursor.fetchone()
        
        # Get status history
        cursor.execute("""
            SELECT * FROM parcel_conditions WHERE parcel_id = %s ORDER BY updated_at DESC
        """, (parcel_id,))
        conditions = cursor.fetchall()
        
        # Get messages
        cursor.execute("""
            SELECT * FROM messages WHERE parcel_id = %s ORDER BY created_at ASC
        """, (parcel_id,))
        messages = cursor.fetchall()
        
        cursor.close()
        return render_template('user_parcel_detail.html', parcel=parcel, courier=courier, 
                             conditions=conditions, messages=messages)
    except Error as e:
        print(f"Error fetching parcel detail: {e}")
        flash('Error fetching parcel details.', 'danger')
        return redirect(url_for('user_dashboard'))
    finally:
        conn.close()

@app.route('/user/parcel/<int:parcel_id>/edit', methods=['GET', 'POST'])
@require_user
def edit_user_parcel(parcel_id):
    """Edit parcel details (only if pending)"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('user_dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            # Get parcel and verify ownership
            cursor.execute("""
                SELECT * FROM parcels WHERE parcel_id = %s AND user_id = %s
            """, (parcel_id, session['user_id']))
            parcel = cursor.fetchone()
            
            if not parcel or parcel['status'] != 'pending':
                flash('Cannot edit this parcel. Only pending parcels can be modified.', 'danger')
                return redirect(url_for('user_dashboard'))
            
            # Get updated values
            receiver_name = request.form.get('receiver_name')
            receiver_phone = request.form.get('receiver_phone')
            receiver_address = request.form.get('receiver_address')
            destination_city = request.form.get('destination_city')
            scheduled_time = request.form.get('scheduled_pickup_time')
            notes = request.form.get('notes')
            
            # Update parcel
            cursor.execute("""
                UPDATE parcels 
                SET receiver_name = %s, receiver_phone = %s, receiver_address = %s,
                    destination_city = %s, scheduled_pickup_time = %s, notes = %s, updated_at = NOW()
                WHERE parcel_id = %s
            """, (receiver_name, receiver_phone, receiver_address, destination_city, 
                  scheduled_time if scheduled_time else None, notes, parcel_id))
            conn.commit()
            
            log_action(session['user_id'], 'Edit Parcel', 'parcel', parcel_id)
            flash('Parcel updated successfully.', 'success')
            return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))
        
        # GET - fetch parcel for editing
        cursor.execute("""
            SELECT * FROM parcels WHERE parcel_id = %s AND user_id = %s
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()
        
        if not parcel:
            flash('Parcel not found.', 'danger')
            return redirect(url_for('user_dashboard'))
        
        if parcel['status'] != 'pending':
            flash('Only pending parcels can be edited.', 'danger')
            return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))
        
        cursor.close()
        return render_template('user_parcel_edit.html', parcel=parcel)
        
    except Error as e:
        print(f"Error editing parcel: {e}")
        flash('Error editing parcel.', 'danger')
        return redirect(url_for('user_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/user/parcel/<int:parcel_id>/cancel', methods=['POST'])
@require_user
def cancel_parcel_user(parcel_id):
    """Cancel parcel booking (only if pending)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get parcel and verify ownership
        cursor.execute("""
            SELECT * FROM parcels WHERE parcel_id = %s AND user_id = %s
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()
        
        if not parcel:
            return jsonify({'error': 'Parcel not found'}), 404
        
        if parcel['status'] != 'pending':
            return jsonify({'error': 'Only pending parcels can be cancelled'}), 400
        
        # Update parcel status to cancelled
        cursor.execute("""
            UPDATE parcels SET status = 'cancelled', updated_at = NOW() WHERE parcel_id = %s
        """, (parcel_id,))
        conn.commit()
        
        log_action(session['user_id'], 'Cancel Parcel', 'parcel', parcel_id)
        
        return jsonify({'success': True, 'message': 'Parcel cancelled successfully'})
    except Error as e:
        print(f"Error cancelling parcel: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/user/parcel/<int:parcel_id>/rate-courier', methods=['POST'])
@require_user
def rate_courier(parcel_id):
    """Rate the courier assigned to a delivered parcel."""
    rating_stars = request.form.get('rating_stars', type=int)
    review_text = request.form.get('review_text', '').strip()

    if rating_stars is None or rating_stars < 1 or rating_stars > 5:
        flash('Please select a rating from 1 to 5 stars.', 'danger')
        return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))

    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.parcel_id, p.status, pa.courier_id, u.full_name AS courier_name
            FROM parcels p
            LEFT JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
            LEFT JOIN users u ON pa.courier_id = u.user_id
            WHERE p.parcel_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
            ORDER BY pa.assigned_at DESC
            LIMIT 1
        """, (parcel_id, session['user_id']))
        parcel = cursor.fetchone()

        if not parcel:
            flash('Parcel not found.', 'danger')
            return redirect(url_for('user_dashboard'))

        if parcel['status'] != 'delivered':
            flash('You can only rate a courier after the parcel has been delivered.', 'warning')
            return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))

        if not parcel.get('courier_id'):
            flash('No courier has been assigned to this parcel yet.', 'warning')
            return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))

        cursor.execute("""
            INSERT INTO courier_ratings (parcel_id, user_id, courier_id, rating_stars, review_text)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                courier_id = VALUES(courier_id),
                rating_stars = VALUES(rating_stars),
                review_text = VALUES(review_text),
                created_at = CURRENT_TIMESTAMP
        """, (parcel_id, session['user_id'], parcel['courier_id'], rating_stars, review_text or None))
        conn.commit()

        log_action(
            session['user_id'],
            'Rate Courier',
            'courier_rating',
            parcel_id,
            new_values={
                'parcel_id': parcel_id,
                'courier_id': parcel['courier_id'],
                'rating_stars': rating_stars,
                'review_text': review_text,
            }
        )

        flash(f'Thanks for rating {parcel["courier_name"] or "the courier"} {rating_stars} star(s).', 'success')
    except Error as e:
        print(f"Error rating courier: {e}")
        flash('Unable to save your rating right now.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('user_parcel_detail', parcel_id=parcel_id))

@app.route('/api/get-available-couriers', methods=['GET'])
@require_user
def get_available_couriers():
    """Get list of available couriers with ratings"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.phone,
                   COUNT(cr.rating_id) as rating_count,
                   ROUND(AVG(cr.rating_stars), 1) as avg_rating
            FROM users u
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE u.role = 'courier' AND u.is_active = TRUE
            GROUP BY u.user_id, u.full_name, u.phone
            ORDER BY avg_rating DESC, u.full_name ASC
        """)
        couriers = cursor.fetchall()
        cursor.close()
        
        return jsonify(couriers)
    except Error as e:
        print(f"Error fetching couriers: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        conn.close()

@app.route('/api/send-message', methods=['POST'])
@require_login
def send_message():
    """Send message to courier or user"""
    try:
        data = request.get_json()
        parcel_id = data.get('parcel_id')
        receiver_id = data.get('receiver_id')
        message_text = data.get('message_text')
        
        if not all([parcel_id, receiver_id, message_text]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection error'}), 500
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO messages (parcel_id, sender_id, receiver_id, message_text, is_read)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (parcel_id, session['user_id'], receiver_id, message_text))
            conn.commit()
            
            log_action(session['user_id'], 'Send Message', 'message', None)
            return jsonify({'success': True})
        except Error as e:
            print(f"Error sending message: {e}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-messages/<int:parcel_id>', methods=['GET'])
@require_login
def get_messages(parcel_id):
    """Get messages for a parcel"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, u.full_name as sender_name, u.role as sender_role
            FROM messages m
            LEFT JOIN users u ON m.sender_id = u.user_id
            WHERE m.parcel_id = %s 
            ORDER BY m.created_at ASC
        """, (parcel_id,))
        messages = cursor.fetchall()
        cursor.close()
        
        # Convert timestamps to string for JSON serialization
        for msg in messages:
            msg['created_at'] = msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(messages)
    except Error as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        conn.close()

# ==================== ERROR HANDLERS ====================

# ==================== ADMIN COURIER MANAGEMENT ====================

@app.route('/admin/couriers')
@require_admin
def admin_couriers():
    """Admin page to manage couriers"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get all couriers with stats
        cursor.execute("""
            SELECT 
                u.user_id, u.full_name, u.username, u.email, u.phone, u.is_active, u.created_at,
                COUNT(p.parcel_id) as parcels_assigned,
                SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                ROUND(SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) / COUNT(p.parcel_id) * 100, 2) as delivery_rate,
                COALESCE(ROUND(AVG(cr.rating_stars), 2), 0) as avg_rating,
                COUNT(DISTINCT cr.rating_id) as total_ratings,
                COALESCE(SUM(CASE WHEN p.status = 'delivered' THEN p.cost_php ELSE 0 END), 0) as total_revenue
            FROM users u
            LEFT JOIN parcel_assignments pa ON u.user_id = pa.courier_id
            LEFT JOIN parcels p ON pa.parcel_id = p.parcel_id AND p.is_deleted = FALSE
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE u.role = 'courier'
            GROUP BY u.user_id, u.full_name, u.username, u.email, u.phone, u.is_active, u.created_at
            ORDER BY u.is_active DESC, u.full_name ASC
        """)
        couriers = cursor.fetchall()
        
        cursor.close()
    except Error as e:
        print(f"Error fetching couriers: {e}")
        flash('Error loading courier data.', 'danger')
        couriers = []
    finally:
        conn.close()
    
    return render_template('admin_couriers.html', couriers=couriers)

@app.route('/admin/couriers/<int:courier_id>/deactivate', methods=['POST'])
@require_admin
def deactivate_courier(courier_id):
    """Deactivate a courier account"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if courier exists
        cursor.execute("SELECT user_id, full_name FROM users WHERE user_id = %s AND role = 'courier'", (courier_id,))
        courier = cursor.fetchone()
        
        if not courier:
            return jsonify({'error': 'Courier not found'}), 404
        
        # Deactivate the courier
        cursor.execute("UPDATE users SET is_active = FALSE WHERE user_id = %s", (courier_id,))
        conn.commit()
        
        log_action(session['user_id'], 'Deactivate Courier', 'courier', courier_id,
                  new_values={'is_active': False})
        
        return jsonify({'success': True, 'message': f'Courier {courier["full_name"]} has been deactivated.'}), 200
    except Error as e:
        print(f"Error deactivating courier: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/couriers/<int:courier_id>/activate', methods=['POST'])
@require_admin
def activate_courier(courier_id):
    """Reactivate a deactivated courier account"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if courier exists
        cursor.execute("SELECT user_id, full_name FROM users WHERE user_id = %s AND role = 'courier'", (courier_id,))
        courier = cursor.fetchone()
        
        if not courier:
            return jsonify({'error': 'Courier not found'}), 404
        
        # Activate the courier
        cursor.execute("UPDATE users SET is_active = TRUE WHERE user_id = %s", (courier_id,))
        conn.commit()
        
        log_action(session['user_id'], 'Activate Courier', 'courier', courier_id,
                  new_values={'is_active': True})
        
        return jsonify({'success': True, 'message': f'Courier {courier["full_name"]} has been reactivated.'}), 200
    except Error as e:
        print(f"Error activating courier: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/couriers/<int:courier_id>/view', methods=['GET'])
@require_admin
def view_courier_details(courier_id):
    """View detailed statistics for a specific courier"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_couriers'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get courier info
        cursor.execute("""
            SELECT 
                u.user_id, u.full_name, u.username, u.email, u.phone, u.is_active, u.created_at,
                COUNT(p.parcel_id) as total_parcels,
                SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN p.status = 'in_transit' THEN 1 ELSE 0 END) as in_transit,
                SUM(CASE WHEN p.status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN p.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                ROUND(SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) / COUNT(p.parcel_id) * 100, 2) as delivery_rate,
                COALESCE(ROUND(AVG(cr.rating_stars), 2), 0) as avg_rating,
                COUNT(DISTINCT cr.rating_id) as total_ratings,
                COALESCE(SUM(CASE WHEN p.status = 'delivered' THEN p.cost_php ELSE 0 END), 0) as total_revenue,
                ROUND(AVG(DATEDIFF(p.updated_at, p.created_at)), 1) as avg_delivery_days
            FROM users u
            LEFT JOIN parcel_assignments pa ON u.user_id = pa.courier_id
            LEFT JOIN parcels p ON pa.parcel_id = p.parcel_id AND p.is_deleted = FALSE
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE u.user_id = %s AND u.role = 'courier'
            GROUP BY u.user_id, u.full_name, u.username, u.email, u.phone, u.is_active, u.created_at
        """, (courier_id,))
        courier = cursor.fetchone()
        
        if not courier:
            flash('Courier not found.', 'warning')
            return redirect(url_for('admin_couriers'))
        
        # Get recent parcels
        cursor.execute("""
            SELECT p.parcel_id, p.tracking_number, p.sender_name, p.receiver_name,
                   p.origin_city, p.destination_city, p.cost_php, p.status, p.created_at
            FROM parcels p
            INNER JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
            WHERE pa.courier_id = %s AND p.is_deleted = FALSE
            ORDER BY p.created_at DESC
            LIMIT 20
        """, (courier_id,))
        recent_parcels = cursor.fetchall()
        
        # Get recent ratings
        cursor.execute("""
            SELECT cr.rating_stars, cr.review_text, cr.created_at, u.full_name
            FROM courier_ratings cr
            LEFT JOIN users u ON cr.user_id = u.user_id
            WHERE cr.courier_id = %s
            ORDER BY cr.created_at DESC
            LIMIT 10
        """, (courier_id,))
        ratings = cursor.fetchall()
        
        cursor.close()
    except Error as e:
        print(f"Error fetching courier details: {e}")
        flash('Error loading courier details.', 'danger')
        return redirect(url_for('admin_couriers'))
    finally:
        conn.close()
    
    return render_template('admin_courier_detail.html', courier=courier, 
                          recent_parcels=recent_parcels, ratings=ratings)

@app.route('/admin/couriers/<int:courier_id>/edit', methods=['GET', 'POST'])
@require_admin
def edit_courier(courier_id):
    """Edit courier information"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_couriers'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            
            if not full_name or not email:
                flash('Name and email are required.', 'danger')
                return redirect(url_for('edit_courier', courier_id=courier_id))
            
            # Get old values for audit log
            cursor.execute("SELECT full_name, email, phone FROM users WHERE user_id = %s", (courier_id,))
            old_values = cursor.fetchone()
            
            cursor.execute("""
                UPDATE users 
                SET full_name = %s, email = %s, phone = %s
                WHERE user_id = %s AND role = 'courier'
            """, (full_name, email, phone, courier_id))
            conn.commit()
            
            new_values = {'full_name': full_name, 'email': email, 'phone': phone}
            log_action(session['user_id'], 'Update Courier Info', 'courier', courier_id,
                      old_values=old_values, new_values=new_values)
            
            flash('Courier information updated successfully.', 'success')
            return redirect(url_for('view_courier_details', courier_id=courier_id))
        
        # GET request
        cursor.execute("""
            SELECT user_id, full_name, email, phone, username, is_active
            FROM users WHERE user_id = %s AND role = 'courier'
        """, (courier_id,))
        courier = cursor.fetchone()
        
        if not courier:
            flash('Courier not found.', 'warning')
            return redirect(url_for('admin_couriers'))
        
        cursor.close()
    except Error as e:
        print(f"Error in edit_courier: {e}")
        flash('Error processing request.', 'danger')
        return redirect(url_for('admin_couriers'))
    finally:
        if cursor:
            cursor.close()
        conn.close()
    
    return render_template('admin_courier_edit.html', courier=courier)

@app.route('/admin/reports/courier-performance')
@require_admin
def courier_performance_report():
    """Generate detailed courier performance report"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get sorted courier performance with all metrics
        cursor.execute("""
            SELECT 
                u.user_id, u.full_name, u.username, u.is_active,
                COUNT(p.parcel_id) as total_parcels,
                SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN p.status = 'in_transit' THEN 1 ELSE 0 END) as in_transit,
                SUM(CASE WHEN p.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                ROUND(SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) / COUNT(p.parcel_id) * 100, 2) as delivery_rate,
                COALESCE(ROUND(AVG(cr.rating_stars), 2), 0) as avg_rating,
                COUNT(DISTINCT cr.rating_id) as total_ratings,
                COALESCE(SUM(CASE WHEN p.status = 'delivered' THEN p.cost_php ELSE 0 END), 0) as total_revenue,
                COALESCE(ROUND(AVG(DATEDIFF(p.updated_at, p.created_at)), 1), 0) as avg_delivery_days
            FROM users u
            LEFT JOIN parcel_assignments pa ON u.user_id = pa.courier_id
            LEFT JOIN parcels p ON pa.parcel_id = p.parcel_id AND p.is_deleted = FALSE
            LEFT JOIN courier_ratings cr ON u.user_id = cr.courier_id
            WHERE u.role = 'courier'
            GROUP BY u.user_id, u.full_name, u.username, u.is_active
            ORDER BY avg_rating DESC, delivery_rate DESC
        """)
        rows = cursor.fetchall()
        # Convert mysql.connector results to standard dicts for Jinja2
        couriers = [dict(row) for row in rows] if rows else []
        
        # Calculate summary statistics in Python (not in Jinja)
        stats = {
            'total_couriers': len(couriers),
            'avg_delivery_rate': 0,
            'avg_rating': 0,
            'total_delivered': 0,
            'total_parcels': 0
        }
        
        if couriers:
            total_delivered = sum((c.get('delivered') or 0) for c in couriers)
            total_parcels = sum((c.get('total_parcels') or 0) for c in couriers)
            delivery_rates = [c.get('delivery_rate') or 0 for c in couriers]
            ratings = [c.get('avg_rating') or 0 for c in couriers if c.get('avg_rating')]

            stats['total_delivered'] = total_delivered
            stats['total_parcels'] = total_parcels
            stats['avg_delivery_rate'] = round(sum(delivery_rates) / len(delivery_rates), 1) if delivery_rates else 0
            stats['avg_rating'] = round(sum(ratings) / len(ratings), 1) if ratings else 0
        
        cursor.close()
    except Error as e:
        print(f"Error fetching performance report: {e}")
        flash('Error loading report.', 'danger')
        couriers = []
        stats = {
            'total_couriers': 0,
            'avg_delivery_rate': 0,
            'avg_rating': 0,
            'total_revenue': 0,
            'total_delivered': 0,
            'total_parcels': 0,
            'avg_delivery_days': 0,
            'success_rate': 0
        }
    finally:
        conn.close()
    
    return render_template('admin_performance_report.html', couriers=couriers, stats=stats)

@app.route('/admin/reports/courier-ratings')
@require_admin
def courier_ratings_report():
    """View all courier ratings with filtering"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Get filter parameters
    min_rating = request.args.get('min_rating', default=0, type=int)
    courier_id = request.args.get('courier_id', default=0, type=int)
    sort_by = request.args.get('sort_by', default='newest')
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get list of couriers for dropdown
        cursor.execute("""
            SELECT user_id, full_name FROM users WHERE role = 'courier' ORDER BY full_name
        """)
        couriers_list = cursor.fetchall()
        
        # Build dynamic query based on filters
        query = """
            SELECT 
                cr.rating_id, cr.rating_stars, cr.review_text, cr.created_at,
                u_courier.full_name as courier_name, u_courier.user_id as courier_id,
                u_user.full_name as user_name,
                p.tracking_number, p.sender_name, p.receiver_name
            FROM courier_ratings cr
            LEFT JOIN users u_courier ON cr.courier_id = u_courier.user_id
            LEFT JOIN users u_user ON cr.user_id = u_user.user_id
            LEFT JOIN parcels p ON cr.parcel_id = p.parcel_id
            WHERE 1=1
        """
        
        params = []
        
        if min_rating > 0:
            query += " AND cr.rating_stars >= %s"
            params.append(min_rating)
        
        if courier_id > 0:
            query += " AND cr.courier_id = %s"
            params.append(courier_id)
        
        # Sort options
        if sort_by == 'oldest':
            query += " ORDER BY cr.created_at ASC"
        elif sort_by == 'highest':
            query += " ORDER BY cr.rating_stars DESC, cr.created_at DESC"
        elif sort_by == 'lowest':
            query += " ORDER BY cr.rating_stars ASC, cr.created_at DESC"
        else:  # newest (default)
            query += " ORDER BY cr.created_at DESC"
        
        query += " LIMIT 100"
        
        cursor.execute(query, params)
        ratings = cursor.fetchall()
        
        cursor.close()
    except Error as e:
        print(f"Error fetching ratings report: {e}")
        flash('Error loading ratings report.', 'danger')
        ratings = []
        couriers_list = []
    finally:
        conn.close()
    
    return render_template('admin_ratings_report.html', 
                          ratings=ratings, 
                          couriers_list=couriers_list,
                          selected_courier_id=courier_id,
                          selected_min_rating=min_rating,
                          selected_sort=sort_by)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
