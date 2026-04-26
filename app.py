import os
import random
import string
from datetime import datetime, timedelta
import math
from functools import wraps

import bcrypt
import mysql.connector
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "freight-logistics-secure-key-2024")
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_SECURE", False)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "freight_logistics"),
}

PH_BOUNDS = {"min_lat": 4.5, "max_lat": 21.5, "min_lng": 116.0, "max_lng": 127.5}
DEFAULT_FLOW_NAME = "Standard Domestic"


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**MYSQL_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False


def log_audit_action(user_id, action, resource_type, resource_id, old_values=None, new_values=None):
    try:
        db = get_db()
        cursor = db.cursor()
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:500]
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, action, resource_type, resource_id, ip_address, user_agent))
        db.commit()
    except Exception as e:
        print(f"Audit logging error: {e}")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def is_within_philippines(latitude, longitude):
    return PH_BOUNDS["min_lat"] <= latitude <= PH_BOUNDS["max_lat"] and PH_BOUNDS["min_lng"] <= longitude <= PH_BOUNDS["max_lng"]


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def estimate_delivery_time(distance_km):
    hours = (distance_km / 40) + 1
    return max(1, min(hours, 48))


def estimate_delivery_cost(distance_km, priority):
    base_cost = 100
    per_km_cost = 5
    priority_multiplier = {"Regular": 1.0, "Express": 1.5, "Critical": 2.0}
    multiplier = priority_multiplier.get(priority, 1.0)
    cost = (base_cost + (distance_km * per_km_cost)) * multiplier
    return round(cost, 2)


def optimize_route_nearest_neighbor(shipments, warehouse_lat, warehouse_lng):
    if not shipments:
        return []
    route = []
    remaining = list(shipments)
    current_lat, current_lng = warehouse_lat, warehouse_lng
    while remaining:
        nearest = min(remaining, key=lambda s: haversine_distance(current_lat, current_lng, s['dest_lat'], s['dest_lng']))
        route.append(nearest)
        remaining.remove(nearest)
        current_lat, current_lng = nearest['dest_lat'], nearest['dest_lng']
    return route


def calculate_route_metrics(route, warehouse_lat, warehouse_lng):
    if not route:
        return {"distance": 0, "time_hours": 0, "cost": 0, "shipment_count": 0, "avg_delivery_time": 0, "avg_cost_per_shipment": 0, "avg_distance_per_delivery": 0, "cost_per_km": 0, "total_weight_kg": 0}
    total_distance = 0
    current_lat, current_lng = warehouse_lat, warehouse_lng
    total_distance += haversine_distance(current_lat, current_lng, route[0]['dest_lat'], route[0]['dest_lng'])
    for i in range(len(route) - 1):
        total_distance += haversine_distance(route[i]['dest_lat'], route[i]['dest_lng'], route[i+1]['dest_lat'], route[i+1]['dest_lng'])
    total_distance += haversine_distance(route[-1]['dest_lat'], route[-1]['dest_lng'], warehouse_lat, warehouse_lng)
    time_hours = estimate_delivery_time(total_distance)
    cost = sum(estimate_delivery_cost(haversine_distance(warehouse_lat, warehouse_lng, ship['dest_lat'], ship['dest_lng']), ship['priority']) for ship in route)
    shipment_count = len(route)
    total_weight = sum(ship.get('weight_kg', 0) for ship in route)
    return {
        "distance": round(total_distance, 2),
        "time_hours": round(time_hours, 2),
        "cost": round(cost, 2),
        "shipment_count": shipment_count,
        "avg_delivery_time": round(time_hours / shipment_count, 2) if shipment_count > 0 else 0,
        "avg_cost_per_shipment": round(cost / shipment_count, 2) if shipment_count > 0 else 0,
        "avg_distance_per_delivery": round(total_distance / shipment_count, 2) if shipment_count > 0 else 0,
        "cost_per_km": round(cost / total_distance, 2) if total_distance > 0 else 0,
        "total_weight_kg": round(total_weight, 2)
    }


def generate_tracking_code(cursor):
    while True:
        stamp = datetime.now().strftime("%y%m%d")
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        code = f"PH{stamp}{suffix}"
        cursor.execute("SELECT 1 FROM shipments WHERE tracking_code = %s", (code,))
        if not cursor.fetchone():
            return code


def get_process_step(cursor, step_order):
    cursor.execute("SELECT step_order, step_name, description FROM process_templates WHERE flow_name = %s AND step_order = %s", (DEFAULT_FLOW_NAME, step_order))
    return cursor.fetchone()


def get_max_step_order(cursor):
    cursor.execute("SELECT MAX(step_order) AS max_step FROM process_templates WHERE flow_name = %s", (DEFAULT_FLOW_NAME,))
    result = cursor.fetchone()
    return result['max_step'] if result and result['max_step'] else 1


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("login"))
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, password_hash, role, full_name, is_active FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user and user["is_active"] and verify_password(password, user["password_hash"]):
                session.permanent = True
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                session["full_name"] = user["full_name"]
                log_audit_action(user["id"], "login", "user", user["id"])
                flash(f"Welcome, {user['full_name']}!", "success")
                return redirect(url_for("dashboard"))
            else:
                log_audit_action(None, "login_failed", "user", None)
                flash("Invalid username or password.", "danger")
        except Exception as e:
            print(f"Login error: {e}")
            flash("Login failed. Please try again.", "danger")
        finally:
            cursor.close()
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not username or not email or not password or not full_name:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("register"))
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "danger")
            return redirect(url_for("register"))
        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("register"))
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash("Username or email already exists.", "danger")
                return redirect(url_for("register"))
            password_hash = hash_password(password)
            cursor.execute("INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active) VALUES (%s, %s, %s, %s, %s, %s, TRUE)", (username, email, password_hash, "courier", full_name, phone))
            db.commit()
            log_audit_action(None, "register", "user", cursor.lastrowid)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.rollback()
            print(f"Registration error: {e}")
            flash("Registration failed. Please try again.", "danger")
        finally:
            cursor.close()
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    log_audit_action(user_id, "logout", "user", user_id)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments")
    total_shipments = cursor.fetchone()["count_rows"]
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments WHERE status = %s", ("Delivered",))
    delivered_count = cursor.fetchone()["count_rows"]
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments WHERE status IN (%s, %s)", ("In Transit", "Out for Delivery"))
    in_transit_count = cursor.fetchone()["count_rows"]
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments WHERE status != %s", ("Delivered",))
    active_count = cursor.fetchone()["count_rows"]
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments WHERE status = %s AND created_at <= DATE_SUB(NOW(), INTERVAL 2 DAY)", ("Booking Confirmed",))
    at_risk_count = cursor.fetchone()["count_rows"]
    cursor.execute("SELECT id, tracking_code, customer_name, origin, destination, status, expected_delivery, updated_at FROM shipments ORDER BY updated_at DESC LIMIT 8")
    latest_shipments = cursor.fetchall()
    cursor.execute("SELECT status, COUNT(*) AS count_rows FROM shipments GROUP BY status ORDER BY count_rows DESC")
    status_breakdown = cursor.fetchall()
    cursor.close()
    return render_template("dashboard.html", total_shipments=total_shipments, delivered_count=delivered_count, in_transit_count=in_transit_count, active_count=active_count, at_risk_count=at_risk_count, latest_shipments=latest_shipments, status_breakdown=status_breakdown)


@app.route("/shipments")
@login_required
def shipments():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    query = request.args.get("q", "").strip()
    if query:
        cursor.execute("SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at FROM shipments WHERE tracking_code LIKE %s OR customer_name LIKE %s OR origin LIKE %s OR destination LIKE %s ORDER BY updated_at DESC", (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at FROM shipments ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    return render_template("shipments.html", shipments=rows, query=query)


@app.route("/shipments/new", methods=["GET", "POST"])
@admin_required
def new_shipment():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        cargo_type = request.form.get("cargo_type", "").strip()
        priority = request.form.get("priority", "Regular").strip()
        expected_delivery = request.form.get("expected_delivery", "").strip() or None
        try:
            weight_kg = float(request.form.get("weight_kg", "0"))
            latitude = float(request.form.get("latitude", "0"))
            longitude = float(request.form.get("longitude", "0"))
        except ValueError:
            flash("Weight and coordinates must be numeric.", "error")
            cursor.close()
            return redirect(url_for("new_shipment"))
        if not all([customer_name, origin, destination, cargo_type]) or weight_kg <= 0:
            flash("Please complete all required fields with valid values.", "error")
            cursor.close()
            return redirect(url_for("new_shipment"))
        if not is_within_philippines(latitude, longitude):
            flash("Initial coordinates must be within the Philippines map bounds.", "error")
            cursor.close()
            return redirect(url_for("new_shipment"))
        first_step = get_process_step(cursor, 1)
        tracking_code = generate_tracking_code(cursor)
        cursor.execute("INSERT INTO shipments (tracking_code, customer_name, origin, destination, cargo_type, weight_kg, priority, status, current_step, expected_delivery, last_lat, last_lng) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (tracking_code, customer_name, origin, destination, cargo_type, weight_kg, priority, first_step['step_name'], 1, expected_delivery, latitude, longitude))
        shipment_id = cursor.lastrowid
        cursor.execute("INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes) VALUES (%s, %s, %s, %s, %s, %s)", (shipment_id, first_step['step_name'], origin, latitude, longitude, "Shipment created and queued for pickup."))
        db.commit()
        log_audit_action(session["user_id"], "create_shipment", "shipment", shipment_id)
        cursor.close()
        flash(f"Shipment created. Tracking Code: {tracking_code}", "success")
        return redirect(url_for("shipments"))
    cursor.close()
    return render_template("shipment_form.html", shipment=None)


@app.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_shipment(shipment_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    shipment = cursor.fetchone()
    if not shipment:
        flash("Shipment not found.", "error")
        cursor.close()
        return redirect(url_for("shipments"))
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        cargo_type = request.form.get("cargo_type", "").strip()
        priority = request.form.get("priority", "Regular").strip()
        expected_delivery = request.form.get("expected_delivery", "").strip() or None
        try:
            weight_kg = float(request.form.get("weight_kg", "0"))
        except ValueError:
            flash("Weight must be numeric.", "error")
            cursor.close()
            return redirect(url_for("edit_shipment", shipment_id=shipment_id))
        if not all([customer_name, origin, destination, cargo_type]) or weight_kg <= 0:
            flash("Please complete all required fields with valid values.", "error")
            cursor.close()
            return redirect(url_for("edit_shipment", shipment_id=shipment_id))
        cursor.execute("UPDATE shipments SET customer_name = %s, origin = %s, destination = %s, cargo_type = %s, weight_kg = %s, priority = %s, expected_delivery = %s WHERE id = %s", (customer_name, origin, destination, cargo_type, weight_kg, priority, expected_delivery, shipment_id))
        db.commit()
        log_audit_action(session["user_id"], "update_shipment", "shipment", shipment_id)
        cursor.close()
        flash("Shipment details updated.", "success")
        return redirect(url_for("shipments"))
    cursor.close()
    return render_template("shipment_form.html", shipment=shipment)


@app.route("/shipments/<int:shipment_id>/advance", methods=["POST"])
@login_required
def advance_process(shipment_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    shipment = cursor.fetchone()
    if not shipment:
        flash("Shipment not found.", "error")
        cursor.close()
        return redirect(url_for("shipments"))
    max_step = get_max_step_order(cursor)
    current_step = shipment["current_step"]
    if current_step >= max_step:
        flash("Shipment already at final process step.", "error")
        cursor.close()
        return redirect(url_for("shipments"))
    next_step = current_step + 1
    step = get_process_step(cursor, next_step)
    location_name = request.form.get("location_name", "").strip() or shipment["destination"]
    notes = request.form.get("notes", "").strip() or step['description']
    latitude = float(shipment["last_lat"]) if shipment["last_lat"] is not None else 14.5995
    longitude = float(shipment["last_lng"]) if shipment["last_lng"] is not None else 120.9842
    cursor.execute("UPDATE shipments SET status = %s, current_step = %s WHERE id = %s", (step['step_name'], next_step, shipment_id))
    cursor.execute("INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes) VALUES (%s, %s, %s, %s, %s, %s)", (shipment_id, step['step_name'], location_name, latitude, longitude, notes))
    db.commit()
    cursor.close()
    flash(f"Process advanced to: {step['step_name']}", "success")
    return redirect(url_for("track_shipment", shipment_id=shipment_id))



@app.route("/api/shipments/<int:shipment_id>/tracking")
@login_required
def shipment_tracking_api(shipment_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, tracking_code, status FROM shipments WHERE id = %s", (shipment_id,))
    shipment = cursor.fetchone()
    if not shipment:
        cursor.close()
        return jsonify({"error": "Shipment not found"}), 404
    cursor.execute("SELECT status, location_name, latitude, longitude, notes, created_at FROM tracking_updates WHERE shipment_id = %s ORDER BY created_at ASC, id ASC", (shipment_id,))
    updates = cursor.fetchall()
    cursor.close()
    return jsonify({"shipment": dict(shipment), "updates": [{**dict(row), "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])} for row in updates], "bounds": PH_BOUNDS})


@app.route("/api/gps/start/<int:shipment_id>", methods=["POST"])
@login_required
def start_gps_tracking(shipment_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM shipments WHERE id = %s", (shipment_id,))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({"error": "Shipment not found"}), 404
    cursor.execute("SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1", (shipment_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        return jsonify({"session_id": existing[0], "message": "GPS tracking already active"}), 200
    cursor.execute("INSERT INTO gps_tracking_sessions (shipment_id, is_active) VALUES (%s, 1)", (shipment_id,))
    session_id = cursor.lastrowid
    db.commit()
    cursor.close()
    return jsonify({"session_id": session_id, "message": "GPS tracking started"}), 201


@app.route("/api/gps/stop/<int:shipment_id>", methods=["POST"])
@login_required
def stop_gps_tracking(shipment_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1", (shipment_id,))
    session_s = cursor.fetchone()
    if not session_s:
        cursor.close()
        return jsonify({"error": "No active GPS session"}), 404
    cursor.execute("UPDATE gps_tracking_sessions SET is_active = 0, ended_at = NOW() WHERE id = %s", (session_s[0],))
    db.commit()
    cursor.close()
    return jsonify({"message": "GPS tracking stopped"}), 200


@app.route("/api/gps/live/<int:shipment_id>")
@login_required
def get_live_gps_data(shipment_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1", (shipment_id,))
    session_s = cursor.fetchone()
    if not session_s:
        cursor.close()
        return jsonify({"error": "No active GPS session"}), 404
    cursor.execute("SELECT latitude, longitude, accuracy_meters, altitude, created_at FROM gps_pings WHERE session_id = %s ORDER BY created_at ASC", (session_s["id"],))
    pings = cursor.fetchall()
    cursor.close()
    return jsonify({"session_id": session_s["id"], "pings": [{**dict(row), "latitude": float(row["latitude"]), "longitude": float(row["longitude"]), "accuracy_meters": float(row["accuracy_meters"]) if row["accuracy_meters"] else None, "altitude": float(row["altitude"]) if row["altitude"] else None, "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])} for row in pings]}), 200


@app.route("/routes")
@login_required
def routes():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, tracking_code, customer_name, origin, destination, priority, status, last_lat, last_lng, weight_kg, cargo_type FROM shipments WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub') ORDER BY priority DESC, created_at ASC LIMIT 50")
    pending_shipments = cursor.fetchall()
    warehouse_lat, warehouse_lng = 14.5995, 120.9842
    shipments_for_opt = []
    for ship in pending_shipments:
        shipments_for_opt.append({'id': ship['id'], 'tracking_code': ship['tracking_code'], 'customer_name': ship['customer_name'], 'destination': ship['destination'], 'priority': ship['priority'], 'cargo_type': ship['cargo_type'], 'weight_kg': float(ship['weight_kg']) if ship['weight_kg'] else 0, 'dest_lat': float(ship['last_lat']) if ship['last_lat'] else 0, 'dest_lng': float(ship['last_lng']) if ship['last_lng'] else 0})
    optimized_route = optimize_route_nearest_neighbor(shipments_for_opt, warehouse_lat, warehouse_lng)
    route_metrics = calculate_route_metrics(optimized_route, warehouse_lat, warehouse_lng)
    prev_lat, prev_lng = warehouse_lat, warehouse_lng
    for i, ship in enumerate(optimized_route):
        ship['distance_from_prev'] = round(haversine_distance(prev_lat, prev_lng, ship['dest_lat'], ship['dest_lng']), 2)
        ship['delivery_time_hrs'] = round(estimate_delivery_time(ship['distance_from_prev']), 2)
        ship['estimated_cost'] = estimate_delivery_cost(ship['distance_from_prev'], ship['priority'])
        ship['route_sequence'] = i + 1
        prev_lat, prev_lng = ship['dest_lat'], ship['dest_lng']
    cursor.execute("SELECT COUNT(*) as count_rows FROM shipments WHERE status = %s AND created_at <= DATE_SUB(NOW(), INTERVAL 2 DAY)", ("Booking Confirmed",))
    at_risk_count = cursor.fetchone()["count_rows"]
    cursor.close()
    return render_template('routes.html', optimized_route=optimized_route, route_metrics=route_metrics, pending_count=len(pending_shipments), at_risk_count=at_risk_count, now=datetime.now())


@app.route("/api/routes/optimize", methods=["POST"])
@login_required
def optimize_routes_api():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    priority_filter = request.json.get('priority', 'all')
    max_shipments = request.json.get('max_shipments', 50)
    if priority_filter != 'all':
        cursor.execute("SELECT id, tracking_code, customer_name, destination, priority, status, last_lat, last_lng FROM shipments WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub') AND priority = %s LIMIT %s", (priority_filter, max_shipments))
    else:
        cursor.execute("SELECT id, tracking_code, customer_name, destination, priority, status, last_lat, last_lng FROM shipments WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub') LIMIT %s", (max_shipments,))
    shipments = cursor.fetchall()
    warehouse_lat, warehouse_lng = 14.5995, 120.9842
    shipments_for_opt = [{'id': s['id'], 'tracking_code': s['tracking_code'], 'destination': s['destination'], 'priority': s['priority'], 'dest_lat': float(s['last_lat']) if s['last_lat'] else 0, 'dest_lng': float(s['last_lng']) if s['last_lng'] else 0} for s in shipments]
    optimized_route = optimize_route_nearest_neighbor(shipments_for_opt, warehouse_lat, warehouse_lng)
    route_metrics = calculate_route_metrics(optimized_route, warehouse_lat, warehouse_lng)
    cursor.close()
    return jsonify({'route': optimized_route, 'metrics': route_metrics, 'shipment_count': len(optimized_route)}), 200


# ============================================================
# ADMIN ROUTES - Courier and Shipment Management
# ============================================================

@app.route("/admin/couriers")
@admin_required
def admin_couriers():
    """Admin dashboard for managing couriers and viewing their performance metrics."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get all active couriers
    cursor.execute("""
        SELECT 
            u.id,
            u.full_name,
            u.phone,
            u.email,
            u.is_active,
            u.created_at,
            COUNT(DISTINCT sa.shipment_id) as assigned_shipments,
            COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as completed_deliveries,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) / 
                  NULLIF(COUNT(DISTINCT sa.shipment_id), 0), 2) as completion_rate
        FROM users u
        LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
        LEFT JOIN shipments s ON sa.shipment_id = s.id
        WHERE u.role = 'courier'
        GROUP BY u.id, u.full_name, u.phone, u.email, u.is_active, u.created_at
        ORDER BY u.full_name ASC
    """)
    couriers = cursor.fetchall()
    cursor.close()
    return render_template("admin_couriers.html", couriers=couriers)


@app.route("/admin/couriers/<int:courier_id>/performance")
@admin_required
def courier_performance_detail(courier_id):
    """View detailed performance metrics for a specific courier."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.callproc('GetCourierPerformanceMetrics', [courier_id])
        results = cursor.fetchall()
        if not results:
            flash("Courier not found.", "danger")
            return redirect(url_for("admin_couriers"))
        
        courier = results[0]
        
        # Get recent shipments
        cursor.execute("""
            SELECT s.id, s.tracking_code, s.customer_name, s.destination_address, s.status, s.created_at
            FROM shipments s
            INNER JOIN shipment_assignments sa ON s.id = sa.shipment_id
            WHERE sa.rider_id = %s
            ORDER BY s.created_at DESC
            LIMIT 10
        """, (courier_id,))
        recent_shipments = cursor.fetchall()
        
        cursor.close()
        return render_template("courier_performance.html", courier=courier, shipments=recent_shipments)
    except Exception as e:
        print(f"Error fetching courier performance: {e}")
        flash("Error loading courier performance.", "danger")
        cursor.close()
        return redirect(url_for("admin_couriers"))


@app.route("/admin/shipments/<int:shipment_id>/assign", methods=["GET", "POST"])
@admin_required
def assign_shipment_to_courier(shipment_id):
    """Assign a shipment to a courier or auto-assign based on optimization."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get shipment details
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    shipment = cursor.fetchone()
    
    if not shipment:
        flash("Shipment not found.", "danger")
        cursor.close()
        return redirect(url_for("shipments"))
    
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        
        try:
            if action == "auto_assign":
                # Use optimized procedure to auto-assign
                cursor.callproc('AssignShipmentOptimized', [shipment_id, session['user_id']])
                results = cursor.fetchall()
                db.commit()
                if results:
                    result = results[0]
                    if result.get('success'):
                        flash(f"Shipment auto-assigned successfully! {result.get('message', '')}", "success")
                    else:
                        flash(f"Auto-assignment failed: {result.get('message', 'Unknown error')}", "danger")
                cursor.close()
                return redirect(url_for("shipments"))
            
            elif action == "manual_assign":
                # Manually assign to selected courier
                courier_id = request.form.get("courier_id", "").strip()
                assignment_notes = request.form.get("notes", "").strip()
                
                if not courier_id:
                    flash("Please select a courier.", "danger")
                    return redirect(url_for("assign_shipment_to_courier", shipment_id=shipment_id))
                
                cursor.execute("SELECT id FROM users WHERE id = %s AND role = 'courier' AND is_active = TRUE", (courier_id,))
                if not cursor.fetchone():
                    flash("Selected courier is not available.", "danger")
                    return redirect(url_for("assign_shipment_to_courier", shipment_id=shipment_id))
                
                cursor.execute("INSERT INTO shipment_assignments (shipment_id, rider_id, assignment_notes) VALUES (%s, %s, %s)", 
                             (shipment_id, courier_id, assignment_notes))
                db.commit()
                log_audit_action(session['user_id'], 'assign_shipment', 'shipment', shipment_id)
                flash("Shipment assigned successfully!", "success")
                cursor.close()
                return redirect(url_for("shipments"))
        
        except Exception as e:
            db.rollback()
            print(f"Assignment error: {e}")
            flash(f"Assignment failed: {str(e)}", "danger")
    
    # GET request - show available couriers
    cursor.execute("""
        SELECT u.id, u.full_name, u.phone,
               COUNT(DISTINCT sa.shipment_id) as current_assignments,
               COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as completed
        FROM users u
        LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
        LEFT JOIN shipments s ON sa.shipment_id = s.id
        WHERE u.role = 'courier' AND u.is_active = TRUE
        GROUP BY u.id, u.full_name, u.phone
        ORDER BY u.full_name ASC
    """)
    couriers = cursor.fetchall()
    cursor.close()
    
    return render_template("assign_shipment.html", shipment=shipment, couriers=couriers)


# ============================================================
# COURIER ROUTES - Courier-Specific Dashboards and Actions
# ============================================================

@app.route("/courier/dashboard")
@login_required
def courier_dashboard():
    """Courier dashboard showing assigned shipments and location tracking status."""
    if session.get("role") != "courier":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard"))
    
    courier_id = session['user_id']
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Get courier's assigned shipments
        cursor.execute("""
            SELECT s.id, s.tracking_code, s.customer_name, s.origin_address, s.destination_address, 
                   s.status, s.weight_kg, s.priority, s.created_at, s.expected_delivery
            FROM shipments s
            INNER JOIN shipment_assignments sa ON s.id = sa.shipment_id
            WHERE sa.rider_id = %s AND s.status NOT IN ('delivered', 'cancelled')
            ORDER BY s.priority DESC, s.created_at ASC
        """, (courier_id,))
        active_shipments = cursor.fetchall()
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT sa.shipment_id) as total_assigned,
                COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as completed,
                COUNT(DISTINCT CASE WHEN s.status IN ('in_transit', 'out_for_delivery') THEN s.id END) as in_progress,
                COUNT(DISTINCT CASE WHEN s.status = 'pending' THEN s.id END) as pending
            FROM shipment_assignments sa
            LEFT JOIN shipments s ON sa.shipment_id = s.id
            WHERE sa.rider_id = %s
        """, (courier_id,))
        stats = cursor.fetchone()
        
        cursor.close()
        return render_template("courier_dashboard.html", shipments=active_shipments, stats=stats)
    
    except Exception as e:
        print(f"Courier dashboard error: {e}")
        cursor.close()
        flash("Error loading dashboard.", "danger")
        return redirect(url_for("dashboard"))


# ============================================================
# GPS TRACKING ROUTES - Courier Location Tracking (Couriers Only)
# ============================================================

@app.route("/api/gps/ping/<int:shipment_id>", methods=["POST"])
@login_required
def record_gps_ping(shipment_id):
    """Record GPS ping for a shipment. Only couriers can submit location data."""
    # Restrict location updates to couriers only
    if session.get("role") != "courier":
        return jsonify({"error": "Only couriers can submit location data"}), 403
    
    db = get_db()
    cursor = db.cursor()
    try:
        data = request.get_json()
        latitude = float(data.get("latitude", 0))
        longitude = float(data.get("longitude", 0))
        accuracy = data.get("accuracy")
        altitude = data.get("altitude")
    except (ValueError, TypeError):
        cursor.close()
        return jsonify({"error": "Invalid GPS data"}), 400
    
    if not is_within_philippines(latitude, longitude):
        cursor.close()
        return jsonify({"error": "Coordinates outside Philippines bounds"}), 400
    
    cursor.execute("SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1", (shipment_id,))
    session_s = cursor.fetchone()
    if not session_s:
        cursor.close()
        return jsonify({"error": "No active GPS session"}), 404
    
    cursor.execute("INSERT INTO gps_pings (session_id, latitude, longitude, accuracy_meters, altitude) VALUES (%s, %s, %s, %s, %s)", 
                  (session_s[0], latitude, longitude, accuracy, altitude))
    cursor.execute("UPDATE shipments SET last_lat = %s, last_lng = %s WHERE id = %s", (latitude, longitude, shipment_id))
    db.commit()
    cursor.close()
    return jsonify({"message": "GPS ping recorded"}), 201


# ============================================================
# Restrict admin from submitting location updates
# ============================================================

@app.route("/shipments/<int:shipment_id>/track", methods=["GET", "POST"])
@login_required
def track_shipment(shipment_id):
    """Track shipment - admins can only view, couriers can update location."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    shipment = cursor.fetchone()
    
    if not shipment:
        flash("Shipment not found.", "error")
        cursor.close()
        return redirect(url_for("shipments"))
    
    # Admins cannot submit location updates
    if request.method == "POST":
        if session.get("role") != "courier":
            flash("Only couriers can submit location updates.", "danger")
            cursor.close()
            return redirect(url_for("track_shipment", shipment_id=shipment_id))
        
        status = request.form.get("status", shipment["status"]).strip() or shipment["status"]
        location_name = request.form.get("location_name", "").strip()
        notes = request.form.get("notes", "").strip() or None
        
        if not location_name:
            flash("Location name is required for tracking updates.", "error")
            cursor.close()
            return redirect(url_for("track_shipment", shipment_id=shipment_id))
        
        try:
            latitude = float(request.form.get("latitude", "0"))
            longitude = float(request.form.get("longitude", "0"))
        except ValueError:
            flash("Latitude and longitude must be numeric.", "error")
            cursor.close()
            return redirect(url_for("track_shipment", shipment_id=shipment_id))
        
        if not is_within_philippines(latitude, longitude):
            flash("Coordinates must be within the Philippines map bounds.", "error")
            cursor.close()
            return redirect(url_for("track_shipment", shipment_id=shipment_id))
        
        cursor.execute("INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes) VALUES (%s, %s, %s, %s, %s, %s)", 
                      (shipment_id, status, location_name, latitude, longitude, notes))
        cursor.execute("UPDATE shipments SET status = %s, last_lat = %s, last_lng = %s WHERE id = %s", 
                      (status, latitude, longitude, shipment_id))
        db.commit()
        cursor.close()
        flash("Tracking update added.", "success")
        return redirect(url_for("track_shipment", shipment_id=shipment_id))
    
    cursor.execute("SELECT id, status, location_name, latitude, longitude, notes, created_at FROM tracking_updates WHERE shipment_id = %s ORDER BY created_at DESC, id DESC", (shipment_id,))
    updates = cursor.fetchall()
    map_points = [{"status": row["status"], "location_name": row["location_name"], "latitude": float(row["latitude"]), "longitude": float(row["longitude"]), "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])} for row in reversed(updates)]
    cursor.close()
    
    # Check if user is courier to show edit form
    is_courier = session.get("role") == "courier"
    return render_template("tracking.html", shipment=shipment, updates=updates, map_points=map_points, ph_bounds=PH_BOUNDS, is_courier=is_courier)


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    print(f"Internal error: {error}")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
