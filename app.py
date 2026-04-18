import os
import random
import string
from datetime import datetime

import mysql.connector
from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "freight-logistics-dev-key")

# MySQL Configuration (XAMPP default)
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


def init_db():
	db = get_db()
	db.executescript(
		"""
		CREATE TABLE IF NOT EXISTS process_templates (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			flow_name TEXT NOT NULL,
			step_order INTEGER NOT NULL,
			step_name TEXT NOT NULL,
			description TEXT,
			UNIQUE(flow_name, step_order)
		);

		CREATE TABLE IF NOT EXISTS shipments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tracking_code TEXT NOT NULL UNIQUE,
			customer_name TEXT NOT NULL,
			origin TEXT NOT NULL,
			destination TEXT NOT NULL,
			cargo_type TEXT NOT NULL,
			weight_kg REAL NOT NULL,
			priority TEXT NOT NULL DEFAULT 'Regular',
			status TEXT NOT NULL,
			current_step INTEGER NOT NULL DEFAULT 1,
			expected_delivery TEXT,
			last_lat REAL,
			last_lng REAL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		);

		CREATE TABLE IF NOT EXISTS tracking_updates (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			shipment_id INTEGER NOT NULL,
			status TEXT NOT NULL,
			location_name TEXT NOT NULL,
			latitude REAL NOT NULL,
			longitude REAL NOT NULL,
			notes TEXT,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
		);

		CREATE TABLE IF NOT EXISTS gps_tracking_sessions (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			shipment_id INTEGER NOT NULL UNIQUE,
			is_active INTEGER NOT NULL DEFAULT 1,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			ended_at TEXT,
			FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
		);

		CREATE TABLE IF NOT EXISTS gps_pings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			session_id INTEGER NOT NULL,
			latitude REAL NOT NULL,
			longitude REAL NOT NULL,
			accuracy_meters REAL,
			altitude REAL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (session_id) REFERENCES gps_tracking_sessions(id) ON DELETE CASCADE
		);

		CREATE INDEX IF NOT EXISTS idx_gps_pings_session ON gps_pings(session_id);
		CREATE INDEX IF NOT EXISTS idx_tracking_updates_shipment ON tracking_updates(shipment_id);
		"""
	)
	db.commit()
	seed_predefined_processes(db)


def seed_predefined_processes(db):
	existing = db.execute(
		"SELECT COUNT(1) AS count_rows FROM process_templates WHERE flow_name = ?",
		(DEFAULT_FLOW_NAME,),
	).fetchone()["count_rows"]
	if existing:
		return

	steps = [
		(DEFAULT_FLOW_NAME, 1, "Booking Confirmed", "Order accepted and validated."),
		(DEFAULT_FLOW_NAME, 2, "Picked Up", "Cargo has been collected from origin."),
		(DEFAULT_FLOW_NAME, 3, "At Origin Hub", "Cargo arrived at the origin sorting hub."),
		(DEFAULT_FLOW_NAME, 4, "In Transit", "Cargo is moving to destination region."),
		(DEFAULT_FLOW_NAME, 5, "At Destination Hub", "Cargo arrived at destination sorting hub."),
		(DEFAULT_FLOW_NAME, 6, "Out for Delivery", "Courier is delivering to recipient."),
		(DEFAULT_FLOW_NAME, 7, "Delivered", "Cargo delivered successfully."),
	]
	db.executemany(
		"""
		INSERT INTO process_templates (flow_name, step_order, step_name, description)
		VALUES (?, ?, ?, ?)
		""",
		steps,
	)
	db.commit()


def is_within_philippines(latitude, longitude):
	return (
		PH_BOUNDS["min_lat"] <= latitude <= PH_BOUNDS["max_lat"]
		and PH_BOUNDS["min_lng"] <= longitude <= PH_BOUNDS["max_lng"]
	)


def generate_tracking_code(db):
	while True:
		stamp = datetime.now().strftime("%y%m%d")
		suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
		code = f"PH{stamp}{suffix}"
		exists = db.execute(
			"SELECT 1 FROM shipments WHERE tracking_code = ?", (code,)
		).fetchone()
		if not exists:
			return code


def get_process_step(db, step_order):
	return db.execute(
		"""
		SELECT step_order, step_name, description
		FROM process_templates
		WHERE flow_name = ? AND step_order = ?
		""",
		(DEFAULT_FLOW_NAME, step_order),
	).fetchone()


def get_max_step_order(db):
	result = db.execute(
		"SELECT MAX(step_order) AS max_step FROM process_templates WHERE flow_name = ?",
		(DEFAULT_FLOW_NAME,),
	).fetchone()
	return result["max_step"] or 1


@app.route("/")
def home():
	return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
	db = get_db()

	total_shipments = db.execute("SELECT COUNT(1) AS count_rows FROM shipments").fetchone()[
		"count_rows"
	]
	delivered_count = db.execute(
		"SELECT COUNT(1) AS count_rows FROM shipments WHERE status = 'Delivered'"
	).fetchone()["count_rows"]
	in_transit_count = db.execute(
		"SELECT COUNT(1) AS count_rows FROM shipments WHERE status IN ('In Transit', 'Out for Delivery')"
	).fetchone()["count_rows"]
	active_count = db.execute(
		"SELECT COUNT(1) AS count_rows FROM shipments WHERE status != 'Delivered'"
	).fetchone()["count_rows"]

	latest_shipments = db.execute(
		"""
		SELECT id, tracking_code, customer_name, origin, destination, status, expected_delivery, updated_at
		FROM shipments
		ORDER BY updated_at DESC
		LIMIT 8
		"""
	).fetchall()

	status_breakdown = db.execute(
		"""
		SELECT status, COUNT(1) AS count_rows
		FROM shipments
		GROUP BY status
		ORDER BY count_rows DESC
		"""
	).fetchall()

	return render_template(
		"dashboard.html",
		total_shipments=total_shipments,
		delivered_count=delivered_count,
		in_transit_count=in_transit_count,
		active_count=active_count,
		latest_shipments=latest_shipments,
		status_breakdown=status_breakdown,
	)


@app.route("/shipments")
def shipments():
	db = get_db()
	query = request.args.get("q", "").strip()

	if query:
		rows = db.execute(
			"""
			SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at
			FROM shipments
			WHERE tracking_code LIKE ?
				OR customer_name LIKE ?
				OR origin LIKE ?
				OR destination LIKE ?
			ORDER BY updated_at DESC
			""",
			(f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
		).fetchall()
	else:
		rows = db.execute(
			"""
			SELECT id, tracking_code, customer_name, origin, destination, cargo_type, priority, status, expected_delivery, updated_at
			FROM shipments
			ORDER BY updated_at DESC
			"""
		).fetchall()

	return render_template("shipments.html", shipments=rows, query=query)


@app.route("/shipments/new", methods=["GET", "POST"])
def new_shipment():
	db = get_db()
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
			return redirect(url_for("new_shipment"))

		if not all([customer_name, origin, destination, cargo_type]) or weight_kg <= 0:
			flash("Please complete all required fields with valid values.", "error")
			return redirect(url_for("new_shipment"))

		if not is_within_philippines(latitude, longitude):
			flash("Initial coordinates must be within the Philippines map bounds.", "error")
			return redirect(url_for("new_shipment"))

		first_step = get_process_step(db, 1)
		tracking_code = generate_tracking_code(db)

		cursor = db.execute(
			"""
			INSERT INTO shipments (
				tracking_code, customer_name, origin, destination, cargo_type, weight_kg,
				priority, status, current_step, expected_delivery, last_lat, last_lng, updated_at
			)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
			""",
			(
				tracking_code,
				customer_name,
				origin,
				destination,
				cargo_type,
				weight_kg,
				priority,
				first_step["step_name"],
				1,
				expected_delivery,
				latitude,
				longitude,
			),
		)
		shipment_id = cursor.lastrowid

		db.execute(
			"""
			INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
			VALUES (?, ?, ?, ?, ?, ?)
			""",
			(
				shipment_id,
				first_step["step_name"],
				origin,
				latitude,
				longitude,
				"Shipment created and queued for pickup.",
			),
		)
		db.commit()

		flash(f"Shipment created. Tracking Code: {tracking_code}", "success")
		return redirect(url_for("shipments"))

	return render_template("shipment_form.html", shipment=None)


@app.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
def edit_shipment(shipment_id):
	db = get_db()
	shipment = db.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
	if not shipment:
		flash("Shipment not found.", "error")
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
			return redirect(url_for("edit_shipment", shipment_id=shipment_id))

		if not all([customer_name, origin, destination, cargo_type]) or weight_kg <= 0:
			flash("Please complete all required fields with valid values.", "error")
			return redirect(url_for("edit_shipment", shipment_id=shipment_id))

		db.execute(
			"""
			UPDATE shipments
			SET customer_name = ?, origin = ?, destination = ?, cargo_type = ?,
				weight_kg = ?, priority = ?, expected_delivery = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
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
		flash("Shipment details updated.", "success")
		return redirect(url_for("shipments"))

	return render_template("shipment_form.html", shipment=shipment)


@app.route("/shipments/<int:shipment_id>/advance", methods=["POST"])
def advance_process(shipment_id):
	db = get_db()
	shipment = db.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
	if not shipment:
		flash("Shipment not found.", "error")
		return redirect(url_for("shipments"))

	max_step = get_max_step_order(db)
	current_step = shipment["current_step"]
	if current_step >= max_step:
		flash("Shipment already at final process step.", "error")
		return redirect(url_for("shipments"))

	next_step = current_step + 1
	step = get_process_step(db, next_step)

	location_name = request.form.get("location_name", "").strip() or shipment["destination"]
	notes = request.form.get("notes", "").strip() or step["description"]

	latitude = shipment["last_lat"] if shipment["last_lat"] is not None else 14.5995
	longitude = shipment["last_lng"] if shipment["last_lng"] is not None else 120.9842

	db.execute(
		"""
		UPDATE shipments
		SET status = ?, current_step = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
		""",
		(step["step_name"], next_step, shipment_id),
	)
	db.execute(
		"""
		INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		(shipment_id, step["step_name"], location_name, latitude, longitude, notes),
	)
	db.commit()

	flash(f"Process advanced to: {step['step_name']}", "success")
	return redirect(url_for("track_shipment", shipment_id=shipment_id))


@app.route("/shipments/<int:shipment_id>/track", methods=["GET", "POST"])
def track_shipment(shipment_id):
	db = get_db()
	shipment = db.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
	if not shipment:
		flash("Shipment not found.", "error")
		return redirect(url_for("shipments"))

	if request.method == "POST":
		status = request.form.get("status", shipment["status"]).strip() or shipment["status"]
		location_name = request.form.get("location_name", "").strip()
		notes = request.form.get("notes", "").strip() or None

		if not location_name:
			flash("Location name is required for tracking updates.", "error")
			return redirect(url_for("track_shipment", shipment_id=shipment_id))

		try:
			latitude = float(request.form.get("latitude", "0"))
			longitude = float(request.form.get("longitude", "0"))
		except ValueError:
			flash("Latitude and longitude must be numeric.", "error")
			return redirect(url_for("track_shipment", shipment_id=shipment_id))

		if not is_within_philippines(latitude, longitude):
			flash("Coordinates must be within the Philippines map bounds.", "error")
			return redirect(url_for("track_shipment", shipment_id=shipment_id))

		db.execute(
			"""
			INSERT INTO tracking_updates (shipment_id, status, location_name, latitude, longitude, notes)
			VALUES (?, ?, ?, ?, ?, ?)
			""",
			(shipment_id, status, location_name, latitude, longitude, notes),
		)
		db.execute(
			"""
			UPDATE shipments
			SET status = ?, last_lat = ?, last_lng = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
			""",
			(status, latitude, longitude, shipment_id),
		)
		db.commit()
		flash("Tracking update added.", "success")
		return redirect(url_for("track_shipment", shipment_id=shipment_id))

	updates = db.execute(
		"""
		SELECT id, status, location_name, latitude, longitude, notes, created_at
		FROM tracking_updates
		WHERE shipment_id = ?
		ORDER BY created_at DESC, id DESC
		""",
		(shipment_id,),
	).fetchall()

	map_points = [
		{
			"status": row["status"],
			"location_name": row["location_name"],
			"latitude": row["latitude"],
			"longitude": row["longitude"],
			"created_at": row["created_at"],
		}
		for row in reversed(updates)
	]

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
	shipment = db.execute(
		"SELECT id, tracking_code, status FROM shipments WHERE id = ?", (shipment_id,)
	).fetchone()
	if not shipment:
		return jsonify({"error": "Shipment not found"}), 404

	updates = db.execute(
		"""
		SELECT status, location_name, latitude, longitude, notes, created_at
		FROM tracking_updates
		WHERE shipment_id = ?
		ORDER BY created_at ASC, id ASC
		""",
		(shipment_id,),
	).fetchall()

	return jsonify(
		{
			"shipment": dict(shipment),
			"updates": [dict(row) for row in updates],
			"bounds": PH_BOUNDS,
		}
	)


@app.route("/api/gps/start/<int:shipment_id>", methods=["POST"])
def start_gps_tracking(shipment_id):
	db = get_db()
	shipment = db.execute(
		"SELECT id FROM shipments WHERE id = ?", (shipment_id,)
	).fetchone()
	if not shipment:
		return jsonify({"error": "Shipment not found"}), 404

	existing = db.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = ? AND is_active = 1",
		(shipment_id,),
	).fetchone()
	if existing:
		return jsonify({"session_id": existing["id"], "message": "GPS tracking already active"}), 200

	cursor = db.execute(
		"""
		INSERT INTO gps_tracking_sessions (shipment_id, is_active, created_at)
		VALUES (?, 1, CURRENT_TIMESTAMP)
		"""
		, (shipment_id,)
	)
	session_id = cursor.lastrowid
	db.commit()

	return jsonify({"session_id": session_id, "message": "GPS tracking started"}), 201


@app.route("/api/gps/stop/<int:shipment_id>", methods=["POST"])
def stop_gps_tracking(shipment_id):
	db = get_db()
	session = db.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = ? AND is_active = 1",
		(shipment_id,),
	).fetchone()
	if not session:
		return jsonify({"error": "No active GPS session"}), 404

	db.execute(
		"""
		UPDATE gps_tracking_sessions
		SET is_active = 0, ended_at = CURRENT_TIMESTAMP
		WHERE id = ?
		""",
		(session["id"],),
	)
	db.commit()
	return jsonify({"message": "GPS tracking stopped"}), 200


@app.route("/api/gps/ping/<int:shipment_id>", methods=["POST"])
def record_gps_ping(shipment_id):
	db = get_db()

	try:
		data = request.get_json()
		latitude = float(data.get("latitude", 0))
		longitude = float(data.get("longitude", 0))
		accuracy = data.get("accuracy")
		altitude = data.get("altitude")
	except (ValueError, TypeError):
		return jsonify({"error": "Invalid GPS data"}), 400

	if not is_within_philippines(latitude, longitude):
		return jsonify({"error": "Coordinates outside Philippines bounds"}), 400

	session = db.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = ? AND is_active = 1",
		(shipment_id,),
	).fetchone()
	if not session:
		return jsonify({"error": "No active GPS session"}), 404

	db.execute(
		"""
		INSERT INTO gps_pings (session_id, latitude, longitude, accuracy_meters, altitude, created_at)
		VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
		""",
		(session["id"], latitude, longitude, accuracy, altitude),
	)
	db.execute(
		"""
		UPDATE shipments
		SET last_lat = ?, last_lng = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
		""",
		(latitude, longitude, shipment_id),
	)
	db.commit()

	return jsonify({"message": "GPS ping recorded"}), 201


@app.route("/api/gps/live/<int:shipment_id>")
def get_live_gps_data(shipment_id):
	db = get_db()
	session = db.execute(
		"SELECT id FROM gps_tracking_sessions WHERE shipment_id = ? AND is_active = 1",
		(shipment_id,),
	).fetchone()
	if not session:
		return jsonify({"error": "No active GPS session"}), 404

	pings = db.execute(
		"""
		SELECT latitude, longitude, accuracy_meters, altitude, created_at
		FROM gps_pings
		WHERE session_id = ?
		ORDER BY created_at ASC
		""",
		(session["id"],),
	).fetchall()

	return jsonify(
		{
			"session_id": session["id"],
			"pings": [dict(row) for row in pings],
		}
	), 200


with app.app_context():
	init_db()


if __name__ == "__main__":
	app.run(debug=True)
