import os
import random
import string
from datetime import datetime, timedelta
import math

import mysql.connector
from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "freight-logistics-dev-key")

# MySQL Configuration (XAMPP defaults: root user, empty password, localhost)
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "freight_logistics"),
}

PH_BOUNDS = {
	"min_lat": 4.5,
	"max_lat": 21.5,
	"min_lng": 116.0,
	"max_lng": 127.5,
}

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


def is_within_philippines(latitude, longitude):
	return (
		PH_BOUNDS["min_lat"] <= latitude <= PH_BOUNDS["max_lat"]
		and PH_BOUNDS["min_lng"] <= longitude <= PH_BOUNDS["max_lng"]
	)



def haversine_distance(lat1, lon1, lat2, lon2):
	"""Calculate distance in km between two coordinates using Haversine formula"""
	R = 6371  # Earth's radius in km
	
	lat1_rad = math.radians(lat1)
	lat2_rad = math.radians(lat2)
	delta_lat = math.radians(lat2 - lat1)
	delta_lon = math.radians(lon2 - lon1)
	
	a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
	c = 2 * math.asin(math.sqrt(a))
	
	return R * c


def estimate_delivery_time(distance_km):
	"""Estimate delivery time in hours based on distance"""
	# Assumes average speed of 40 km/h for road transport
	# Plus 1 hour for processing at each hub
	hours = (distance_km / 40) + 1
	return max(1, min(hours, 48))  # Between 1-48 hours


def estimate_delivery_cost(distance_km, priority):
	"""Estimate delivery cost based on distance and priority"""
	base_cost = 100  # PHP base cost
	per_km_cost = 5  # PHP per km
	priority_multiplier = {"Regular": 1.0, "Express": 1.5, "Critical": 2.0}
	
	multiplier = priority_multiplier.get(priority, 1.0)
	cost = (base_cost + (distance_km * per_km_cost)) * multiplier
	
	return round(cost, 2)


def optimize_route_nearest_neighbor(shipments, warehouse_lat, warehouse_lng):
	"""Optimize route using nearest neighbor algorithm"""
	if not shipments:
		return []
	
	route = []
	remaining = list(shipments)
	current_lat, current_lng = warehouse_lat, warehouse_lng
	
	while remaining:
		nearest = min(
			remaining,
			key=lambda s: haversine_distance(current_lat, current_lng, s['dest_lat'], s['dest_lng'])
		)
		route.append(nearest)
		remaining.remove(nearest)
		current_lat, current_lng = nearest['dest_lat'], nearest['dest_lng']
	
	return route


def calculate_route_metrics(route, warehouse_lat, warehouse_lng):
	"""Calculate total distance, time, and cost for a route"""
	if not route:
		return {"distance": 0, "time_hours": 0, "cost": 0, "shipment_count": 0}
	
	total_distance = 0
	current_lat, current_lng = warehouse_lat, warehouse_lng
	
	# Distance from warehouse to first stop
	total_distance += haversine_distance(current_lat, current_lng, route[0]['dest_lat'], route[0]['dest_lng'])
	
	# Distance between stops
	for i in range(len(route) - 1):
		total_distance += haversine_distance(
			route[i]['dest_lat'], route[i]['dest_lng'],
			route[i+1]['dest_lat'], route[i+1]['dest_lng']
		)
	
	# Distance back to warehouse
	total_distance += haversine_distance(route[-1]['dest_lat'], route[-1]['dest_lng'], warehouse_lat, warehouse_lng)
	
	time_hours = estimate_delivery_time(total_distance)
	cost = sum(estimate_delivery_cost(
		haversine_distance(warehouse_lat, warehouse_lng, ship['dest_lat'], ship['dest_lng']),
		ship['priority']
	) for ship in route)
	
	return {
		"distance": round(total_distance, 2),
		"time_hours": round(time_hours, 2),
		"cost": round(cost, 2),
		"shipment_count": len(route)
	}


def auto_cancel_overdue_shipments(db):
	"""Auto-cancel 'Booking Confirmed' shipments not processed for 3+ days"""
	try:
		# Create a separate non-dictionary cursor for this operation
		cursor = db.cursor()
		
		three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
		
		# Find shipments stuck in 'Booking Confirmed' for 3+ days
		cursor.execute(
			"""
			SELECT id, tracking_code FROM shipments
			WHERE status = 'Booking Confirmed' AND created_at <= %s
			""",
			(three_days_ago,)
		)
		old_shipments = cursor.fetchall()
		
		cancelled_count = 0
		for shipment in old_shipments:
			shipment_id = shipment[0]
			tracking_code = shipment[1]
			
			# Update status to Cancelled
			cursor.execute(
				"""
				UPDATE shipments
				SET status = 'Cancelled', updated_at = %s
				WHERE id = %s
				""",
				(datetime.now().isoformat(), shipment_id)
			)
			
			# Add cancellation note
			cursor.execute(
				"""
				INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes, created_at)
				VALUES (%s, %s, %s, %s, %s, %s, %s)
				""",
				(shipment_id, 'Cancelled', 'System', 0.0, 0.0, 'Auto-cancelled: Not processed within 3 days', datetime.now().isoformat())
			)
			
			cancelled_count += 1
		
		if cancelled_count > 0:
			db.commit()
		
		cursor.close()
		return cancelled_count
	except Exception as e:
		print(f"Error in auto_cancel_overdue_shipments: {e}")
		return 0


def generate_tracking_code(cursor):
	while True:
		stamp = datetime.now().strftime("%y%m%d")
		suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
		code = f"PH{stamp}{suffix}"
		cursor.execute("SELECT 1 FROM shipments WHERE tracking_code = %s", (code,))
		if not cursor.fetchone():
			return code


def get_process_step(cursor, step_order):
	cursor.execute(
		"""
		SELECT step_order, step_name, description
		FROM process_templates
		WHERE flow_name = %s AND step_order = %s
		""",
		(DEFAULT_FLOW_NAME, step_order),
	)
	return cursor.fetchone()


def get_max_step_order(cursor):
	cursor.execute(
		"SELECT MAX(step_order) AS max_step FROM process_templates WHERE flow_name = %s",
		(DEFAULT_FLOW_NAME,),
	)
	result = cursor.fetchone()
	return result['max_step'] if result and result['max_step'] else 1


@app.route("/")
def home():
	return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
	db = get_db()
	cursor = db.cursor(dictionary=True)
	
	# Auto-cancel overdue shipments
	auto_cancel_overdue_shipments(db)

	cursor.execute("SELECT COUNT(*) as count_rows FROM shipments")
	total_shipments = cursor.fetchone()["count_rows"]

	cursor.execute(
		"SELECT COUNT(*) as count_rows FROM shipments WHERE status = %s", ("Delivered",)
	)
	delivered_count = cursor.fetchone()["count_rows"]

	cursor.execute(
		"SELECT COUNT(*) as count_rows FROM shipments WHERE status IN (%s, %s)",
		("In Transit", "Out for Delivery"),
	)
	in_transit_count = cursor.fetchone()["count_rows"]

	cursor.execute(
		"SELECT COUNT(*) as count_rows FROM shipments WHERE status != %s", ("Delivered",)
	)
	active_count = cursor.fetchone()["count_rows"]
	
	# Count at-risk shipments (Booking Confirmed for 2+ days)
	two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
	cursor.execute(
		"""
		SELECT COUNT(*) as count_rows FROM shipments
		WHERE status = 'Booking Confirmed' AND created_at <= %s
		""",
		(two_days_ago,)
	)
	at_risk_count = cursor.fetchone()["count_rows"]

	cursor.execute(
		"""
		SELECT id, tracking_code, customer_name, origin, destination, status, expected_delivery, updated_at
		FROM shipments
		ORDER BY updated_at DESC
		LIMIT 8
		"""
	)
	latest_shipments = cursor.fetchall()

	cursor.execute(
		"""
		SELECT status, COUNT(*) AS count_rows
		FROM shipments
		GROUP BY status
		ORDER BY count_rows DESC
		"""
	)
	status_breakdown = cursor.fetchall()

	cursor.close()

	return render_template(
		"dashboard.html",
		total_shipments=total_shipments,
		delivered_count=delivered_count,
		in_transit_count=in_transit_count,
		active_count=active_count,
		at_risk_count=at_risk_count,
		latest_shipments=latest_shipments,
		status_breakdown=status_breakdown,
	)


@app.route("/shipments")
def shipments():
	db = get_db()
	cursor = db.cursor(dictionary=True)
	query = request.args.get("q", "").strip()

	if query:
		cursor.execute(
			"""
			SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at
			FROM shipments
			WHERE tracking_code LIKE %s
				OR customer_name LIKE %s
				OR origin LIKE %s
				OR destination LIKE %s
			ORDER BY updated_at DESC
			""",
			(f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
		)
	else:
		cursor.execute(
			"""
			SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at
			FROM shipments
			ORDER BY updated_at DESC
			"""
		)

	rows = cursor.fetchall()
	cursor.close()

	return render_template("shipments.html", shipments=rows, query=query)


@app.route("/shipments/new", methods=["GET", "POST"])
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

		cursor.execute(
			"""
			INSERT INTO shipments (
				tracking_code, customer_name, origin, destination, cargo_type, weight_kg,
				priority, status, current_step, expected_delivery, last_lat, last_lng
			)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",
			(
				tracking_code,
				customer_name,
				origin,
				destination,
				cargo_type,
				weight_kg,
				priority,
				first_step['step_name'],
				1,
				expected_delivery,
				latitude,
				longitude,
			),
		)
		shipment_id = cursor.lastrowid

		cursor.execute(
			"""
			INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
			VALUES (%s, %s, %s, %s, %s, %s)
			""",
			(
				shipment_id,
				first_step['step_name'],
				origin,
				latitude,
				longitude,
				"Shipment created and queued for pickup.",
			),
		)
		db.commit()
		cursor.close()

		flash(f"Shipment created. Tracking Code: {tracking_code}", "success")
		return redirect(url_for("shipments"))

	cursor.close()
	return render_template("shipment_form.html", shipment=None)


@app.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
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

		cursor.execute(
			"""
			UPDATE shipments
			SET customer_name = %s, origin = %s, destination = %s, cargo_type = %s,
				weight_kg = %s, priority = %s, expected_delivery = %s
			WHERE id = %s
			""",
			(
				customer_name,
				origin,
				destination,
				cargo_type,
				weight_kg,
				priority,
				expected_delivery,
				shipment_id,
			),
		)
		db.commit()
		cursor.close()
		flash("Shipment details updated.", "success")
		return redirect(url_for("shipments"))

	cursor.close()
	return render_template("shipment_form.html", shipment=shipment)


@app.route("/shipments/<int:shipment_id>/advance", methods=["POST"])
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

	cursor.execute(
		"""
		UPDATE shipments
		SET status = %s, current_step = %s
		WHERE id = %s
		""",
		(step['step_name'], next_step, shipment_id),
	)
	cursor.execute(
		"""
		INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
		VALUES (%s, %s, %s, %s, %s, %s)
		""",
		(shipment_id, step['step_name'], location_name, latitude, longitude, notes),
	)
	db.commit()
	cursor.close()

	flash(f"Process advanced to: {step['step_name']}", "success")
	return redirect(url_for("track_shipment", shipment_id=shipment_id))


@app.route("/shipments/<int:shipment_id>/track", methods=["GET", "POST"])
def track_shipment(shipment_id):
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
	shipment = cursor.fetchone()

	if not shipment:
		flash("Shipment not found.", "error")
		cursor.close()
		return redirect(url_for("shipments"))

	if request.method == "POST":
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

		cursor.execute(
			"""
			INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
			VALUES (%s, %s, %s, %s, %s, %s)
			""",
			(shipment_id, status, location_name, latitude, longitude, notes),
		)
		cursor.execute(
			"""
			UPDATE shipments
			SET status = %s, last_lat = %s, last_lng = %s
			WHERE id = %s
			""",
			(status, latitude, longitude, shipment_id),
		)
		db.commit()
		cursor.close()
		flash("Tracking update added.", "success")
		return redirect(url_for("track_shipment", shipment_id=shipment_id))

	cursor.execute(
		"""
		SELECT id, status, location_name, latitude, longitude, notes, created_at
		FROM tracking_updates
		WHERE shipment_id = %s
		ORDER BY created_at DESC, id DESC
		""",
		(shipment_id,),
	)
	updates = cursor.fetchall()

	map_points = [
		{
			"status": row["status"],
			"location_name": row["location_name"],
			"latitude": float(row["latitude"]),
			"longitude": float(row["longitude"]),
			"created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"]),
		}
		for row in reversed(updates)
	]

	cursor.close()

	return render_template(
		"tracking.html",
		shipment=shipment,
		updates=updates,
		map_points=map_points,
		ph_bounds=PH_BOUNDS,
	)


@app.route("/api/shipments/<int:shipment_id>/tracking")
def shipment_tracking_api(shipment_id):
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute(
		"SELECT id, tracking_code, status FROM shipments WHERE id = %s", (shipment_id,)
	)
	shipment = cursor.fetchone()

	if not shipment:
		cursor.close()
		return jsonify({"error": "Shipment not found"}), 404

	cursor.execute(
		"""
		SELECT status, location_name, latitude, longitude, notes, created_at
		FROM tracking_updates
		WHERE shipment_id = %s
		ORDER BY created_at ASC, id ASC
		""",
		(shipment_id,),
	)
	updates = cursor.fetchall()
	cursor.close()

	return jsonify(
		{
			"shipment": dict(shipment),
			"updates": [
				{**dict(row), "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])}
				for row in updates
			],
			"bounds": PH_BOUNDS,
		}
	)


@app.route("/api/gps/start/<int:shipment_id>", methods=["POST"])
def start_gps_tracking(shipment_id):
	db = get_db()
	cursor = db.cursor()

	cursor.execute("SELECT id FROM shipments WHERE id = %s", (shipment_id,))
	if not cursor.fetchone():
		cursor.close()
		return jsonify({"error": "Shipment not found"}), 404

	cursor.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1",
		(shipment_id,),
	)
	existing = cursor.fetchone()
	if existing:
		cursor.close()
		return jsonify({"session_id": existing[0], "message": "GPS tracking already active"}), 200

	cursor.execute(
		"""
		INSERT INTO gps_tracking_sessions (shipment_id, is_active)
		VALUES (%s, 1)
		""",
		(shipment_id,),
	)
	session_id = cursor.lastrowid
	db.commit()
	cursor.close()

	return jsonify({"session_id": session_id, "message": "GPS tracking started"}), 201


@app.route("/api/gps/stop/<int:shipment_id>", methods=["POST"])
def stop_gps_tracking(shipment_id):
	db = get_db()
	cursor = db.cursor()

	cursor.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1",
		(shipment_id,),
	)
	session = cursor.fetchone()
	if not session:
		cursor.close()
		return jsonify({"error": "No active GPS session"}), 404

	cursor.execute(
		"""
		UPDATE gps_tracking_sessions
		SET is_active = 0, ended_at = NOW()
		WHERE id = %s
		""",
		(session[0],),
	)
	db.commit()
	cursor.close()
	return jsonify({"message": "GPS tracking stopped"}), 200


@app.route("/api/gps/ping/<int:shipment_id>", methods=["POST"])
def record_gps_ping(shipment_id):
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

	cursor.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1",
		(shipment_id,),
	)
	session = cursor.fetchone()
	if not session:
		cursor.close()
		return jsonify({"error": "No active GPS session"}), 404

	cursor.execute(
		"""
		INSERT INTO gps_pings (session_id, latitude, longitude, accuracy_meters, altitude)
		VALUES (%s, %s, %s, %s, %s)
		""",
		(session[0], latitude, longitude, accuracy, altitude),
	)
	cursor.execute(
		"""
		UPDATE shipments
		SET last_lat = %s, last_lng = %s
		WHERE id = %s
		""",
		(latitude, longitude, shipment_id),
	)
	db.commit()
	cursor.close()

	return jsonify({"message": "GPS ping recorded"}), 201


@app.route("/api/gps/live/<int:shipment_id>")
def get_live_gps_data(shipment_id):
	db = get_db()
	cursor = db.cursor(dictionary=True)

	cursor.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = %s AND is_active = 1",
		(shipment_id,),
	)
	session = cursor.fetchone()
	if not session:
		cursor.close()
		return jsonify({"error": "No active GPS session"}), 404

	cursor.execute(
		"""
		SELECT latitude, longitude, accuracy_meters, altitude, created_at
		FROM gps_pings
		WHERE session_id = %s
		ORDER BY created_at ASC
		""",
		(session["id"],),
	)
	pings = cursor.fetchall()
	cursor.close()

	return jsonify(
		{
			"session_id": session["id"],
			"pings": [
				{
					**dict(row),
					"latitude": float(row["latitude"]),
					"longitude": float(row["longitude"]),
					"accuracy_meters": float(row["accuracy_meters"]) if row["accuracy_meters"] else None,
					"altitude": float(row["altitude"]) if row["altitude"] else None,
					"created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"]),
				}
				for row in pings
			],
		}
	), 200


@app.route("/routes")
def routes():
	"""Display optimized delivery routes"""
	db = get_db()
	cursor = db.cursor(dictionary=True)
	
	# Auto-cancel overdue shipments
	auto_cancel_overdue_shipments(db)
	
	# Get pending shipments (not yet In Transit)
	cursor.execute(
		"""
		SELECT id, tracking_code, customer_name, origin, destination, priority, status,
		       last_lat, last_lng, weight_kg, cargo_type
		FROM shipments
		WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub')
		ORDER BY priority DESC, created_at ASC
		LIMIT 50
		"""
	)
	pending_shipments = cursor.fetchall()
	
	# Check for at-risk shipments (Booking Confirmed for 2+ days)
	two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
	cursor.execute(
		"""
		SELECT id, tracking_code, customer_name, destination, created_at FROM shipments
		WHERE status = 'Booking Confirmed' AND created_at <= %s
		""",
		(two_days_ago,)
	)
	at_risk_shipments = cursor.fetchall()
	
	# Manila warehouse coordinates (central hub)
	warehouse_lat, warehouse_lng = 14.5995, 120.9842
	
	# Prepare shipments for optimization - convert Decimal to float
	shipments_for_opt = []
	for ship in pending_shipments:
		shipments_for_opt.append({
			'id': ship['id'],
			'tracking_code': ship['tracking_code'],
			'customer_name': ship['customer_name'],
			'destination': ship['destination'],
			'priority': ship['priority'],
			'cargo_type': ship['cargo_type'],
			'weight_kg': float(ship['weight_kg']) if ship['weight_kg'] else 0,
			'dest_lat': float(ship['last_lat']) if ship['last_lat'] else 0,
			'dest_lng': float(ship['last_lng']) if ship['last_lng'] else 0
		})
	
	# Generate optimized route
	optimized_route = optimize_route_nearest_neighbor(shipments_for_opt, warehouse_lat, warehouse_lng)
	route_metrics = calculate_route_metrics(optimized_route, warehouse_lat, warehouse_lng)
	
	# Add distance to each shipment in route
	prev_lat, prev_lng = warehouse_lat, warehouse_lng
	for i, ship in enumerate(optimized_route):
		ship['distance_from_prev'] = round(haversine_distance(prev_lat, prev_lng, ship['dest_lat'], ship['dest_lng']), 2)
		ship['delivery_time_hrs'] = round(estimate_delivery_time(ship['distance_from_prev']), 2)
		ship['estimated_cost'] = estimate_delivery_cost(ship['distance_from_prev'], ship['priority'])
		ship['route_sequence'] = i + 1
		prev_lat, prev_lng = ship['dest_lat'], ship['dest_lng']
	
	cursor.close()
	
	return render_template(
		'routes.html',
		optimized_route=optimized_route,
		route_metrics=route_metrics,
		at_risk_shipments=at_risk_shipments,
		pending_count=len(pending_shipments),
		at_risk_count=len(at_risk_shipments),
		now=datetime.now()
	)


@app.route("/api/routes/optimize", methods=["POST"])
def optimize_routes_api():
	"""API endpoint for route optimization"""
	db = get_db()
	cursor = db.cursor(dictionary=True)
	
	priority_filter = request.json.get('priority', 'all')
	max_shipments = request.json.get('max_shipments', 50)
	
	# Build query based on priority
	if priority_filter != 'all':
		cursor.execute(
			"""
			SELECT id, tracking_code, customer_name, destination, priority, status, last_lat, last_lng
			FROM shipments
			WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub') AND priority = %s
			LIMIT %s
			""",
			(priority_filter, max_shipments)
		)
	else:
		cursor.execute(
			"""
			SELECT id, tracking_code, customer_name, destination, priority, status, last_lat, last_lng
			FROM shipments
			WHERE status IN ('Booking Confirmed', 'Picked Up', 'At Origin Hub')
			LIMIT %s
			""",
			(max_shipments,)
		)
	
	shipments = cursor.fetchall()
	
	warehouse_lat, warehouse_lng = 14.5995, 120.9842
	
	# Convert Decimal to float for optimization
	shipments_for_opt = [{
		'id': s['id'],
		'tracking_code': s['tracking_code'],
		'destination': s['destination'],
		'priority': s['priority'],
		'dest_lat': float(s['last_lat']) if s['last_lat'] else 0,
		'dest_lng': float(s['last_lng']) if s['last_lng'] else 0
	} for s in shipments]
	
	optimized_route = optimize_route_nearest_neighbor(shipments_for_opt, warehouse_lat, warehouse_lng)
	route_metrics = calculate_route_metrics(optimized_route, warehouse_lat, warehouse_lng)
	
	cursor.close()
	
	return jsonify({
		'route': optimized_route,
		'metrics': route_metrics,
		'shipment_count': len(optimized_route)
	}), 200


if __name__ == "__main__":
	app.run(debug=True)
