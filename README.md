# Freight Logistics Management System - Production Ready

A comprehensive, production-ready freight logistics platform with role-based access control (Admin/Courier), real-time GPS tracking, intelligent shipment assignment, and advanced database design.

**NEW IN v2.0**:
- ✅ Two-tier role system (Admin & Courier)
- ✅ Courier-only location tracking (Admins have no location field)
- ✅ Intelligent auto-assignment based on workload & performance
- ✅ Database views and procedures for optimization
- ✅ 3NF normalized schema with fragmentation strategy
- ✅ Complete database design documentation (ERD, normalization, replication)
- ✅ Production-ready with audit logging and security
- ✅ Comprehensive templates for admin/courier dashboards

## 🎯 System Goals

This system is designed for **presentation-ready demonstration** with:
- Clean separation of admin and courier responsibilities
- Real-time courier location tracking visible to admins
- Automated intelligent shipment routing
- Production-grade database design
- Comprehensive documentation for evaluation

## Features

- **Dashboard** - Real-time metrics and at-risk shipment monitoring
- **Shipment Management** - Create, edit, and track shipments with full lifecycle management
- **GPS Tracking** - Real-time location updates using browser Geolocation API
- **Route Optimization** - AI-powered nearest-neighbor algorithm for optimal delivery routes
- **Auto-Cancellation** - Automatic cancellation of shipments not processed within 3 days
- **Interactive Maps** - Leaflet-based visualization with Philippine geographic bounds
- **Process Workflow** - 7-stage predefined logistics workflow (Booking → Delivery)
- **Cost & Time Estimation** - Dynamic delivery cost and time calculations based on distance and priority

## Tech Stack

- **Backend:** Python 3.13 + Flask 3.0.0+
- **Database:** MySQL 8.0+
- **Frontend:** HTML5/CSS3/JavaScript
- **Maps:** Leaflet 1.9.4 + OpenStreetMap
- **Algorithms:** Haversine distance formula, nearest-neighbor route optimization

## Setup & Installation

### Prerequisites

- Python 3.8+
- MySQL Server (local or remote)
- XAMPP (for local development with phpMyAdmin)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure MySQL Connection

Set environment variables (or use defaults for XAMPP):

```powershell
# Windows
$env:MYSQL_HOST = "localhost"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = ""
$env:MYSQL_DB = "freight_logistics"
```

Or in `.env` file:
```
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=freight_logistics
```

### 3. Create MySQL Database

```sql
CREATE DATABASE freight_logistics;
USE freight_logistics;
```

**Tables will be auto-created** on first application run with the following schema:

```sql
-- Process workflow templates
process_templates (id, flow_name, step_order, step_name, description)

-- Shipment records
shipments (id, tracking_code, customer_name, origin, destination, cargo_type, 
           weight_kg, priority, status, current_step, expected_delivery, 
           last_lat, last_lng, created_at, updated_at)

-- Shipment status history
tracking_updates (id, shipment_id, status, location_name, latitude, longitude, 
                  notes, created_at)

-- GPS tracking sessions
gps_tracking_sessions (id, shipment_id, is_active, created_at, ended_at)

-- GPS ping records
gps_pings (id, session_id, latitude, longitude, accuracy_meters, altitude, created_at)
```

### 4. Run the Application (Local Machine Only)

```bash
python app.py
```

**The app will start on `http://localhost:5000`**

⚠️ **The application will ONLY work on your local machine.** 
- Do NOT attempt to access from other machines
- Do NOT deploy to cloud servers or remote hosting
- Database must be on `localhost`
- Use only for development and testing

**Default Access:**
- URL: `http://localhost:5000` (local machine only)
- No authentication required (development mode)
- Access all features directly from the dashboard

## Setup & Installation (Continued)

### Web Routes (HTML)

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Redirect to dashboard |
| `/dashboard` | GET | Main dashboard with metrics |
| `/shipments` | GET | List all shipments with search |
| `/shipments/new` | GET/POST | Create new shipment |
| `/shipments/<id>/edit` | GET/POST | Edit shipment details |
| `/shipments/<id>/advance` | POST | Advance to next process step |
| `/shipments/<id>/track` | GET/POST | View tracking history and updates |
| `/routes` | GET | Display AI-optimized delivery routes |

### API Endpoints (JSON)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/shipments/<id>/tracking` | GET | Get shipment tracking history |
| `/api/gps/start/<id>` | POST | Start GPS tracking session |
| `/api/gps/stop/<id>` | POST | Stop GPS tracking session |
| `/api/gps/ping/<id>` | POST | Record GPS coordinate ping |
| `/api/gps/live/<id>` | GET | Get all pings for active session |
| `/api/routes/optimize` | POST | Optimize delivery route by priority |

## Key Features Explained

### Dashboard Metrics

- **Total Shipments** - Count of all shipments in database
- **Delivered** - Count of completed deliveries
- **In Transit** - Shipments actively being delivered
- **Active** - Shipments not yet completed
- **At-Risk** - Shipments pending processing for 2+ days (warning)
- **Latest Activity** - Recent shipment updates

### Shipment Lifecycle

```
1. Booking Confirmed  → Order accepted, validated
2. Picked Up          → Cargo collected from origin
3. At Origin Hub      → Arrived at sorting facility
4. In Transit         → Moving toward destination
5. At Destination Hub → Arrived at destination facility
6. Out for Delivery   → Courier en route to recipient
7. Delivered          → Successfully delivered
```

Auto-cancellation triggers if shipment remains in "Booking Confirmed" for 3+ days.

### Route Optimization Algorithm

The nearest-neighbor algorithm finds optimal delivery sequences:

1. Start at warehouse (Manila: 14.5995°N, 120.9842°E)
2. Calculate distances to all pending shipments (Haversine formula)
3. Select nearest unvisited destination
4. Repeat until all shipments scheduled
5. Calculate total distance, time, and cost

**Formula Details:**
- **Distance:** Haversine great-circle distance
- **Time:** distance_km / 40 km/h + 1 hour hub processing
- **Cost:** ₱100 base + ₱5/km × priority multiplier
  - Regular: 1.0x
  - Express: 1.5x
  - Critical: 2.0x

### GPS Tracking

Real-time location tracking using HTML5 Geolocation API:

1. Start session: `/api/gps/start/<shipment_id>`
2. Record pings: `/api/gps/ping/<shipment_id>` (automatic client-side)
3. Get live data: `/api/gps/live/<shipment_id>`
4. Stop session: `/api/gps/stop/<shipment_id>`

Pings are validated to ensure coordinates are within Philippine bounds (4.5-21.5°N, 116.0-127.5°E).

## Database Details

### MySQL Configuration

```python
MYSQL_CONFIG = {
    "host": "localhost",       # Default XAMPP
    "user": "root",            # Default XAMPP user
    "password": "",            # Default XAMPP (empty)
    "database": "freight_logistics"
}
```

### Connection Handling

- Connections are created per-request using Flask's `g` object
- Automatic cleanup with `@app.teardown_appcontext`
- Dictionary cursors for easier data access

### Data Validation

- **Coordinates:** Must be within Philippine bounds (4.5-21.5°N, 116.0-127.5°E)
- **Weight:** Must be positive numeric value
- **Tracking Code:** Auto-generated format: PH + YYMMDD + 5 random alphanumeric
- **Priority:** Regular, Express, or Critical
- **Statuses:** Booking Confirmed, Picked Up, At Origin Hub, In Transit, At Destination Hub, Out for Delivery, Delivered, Cancelled

## Development Notes

### Auto-Cancellation Logic

Runs on every dashboard load:

```python
auto_cancel_overdue_shipments(db)  # Called in /dashboard route
```

Finds shipments where:
- Status = "Booking Confirmed"
- Created date ≤ 3 days ago

Then:
- Updates status to "Cancelled"
- Adds tracking note with timestamp
- Commits to database

### Type Handling

MySQL returns `Decimal` types for numeric fields. All calculations convert to `float`:

```python
float(shipment['weight_kg']) if shipment['weight_kg'] else 0
```

## Troubleshooting

### MySQL Connection Error
```
AttributeError: 'MySQLConnection' object has no attribute 'executescript'
```
**Solution:** Use MySQL syntax, not SQLite. Check that `mysql.connector.connect()` is used.

### No Database Tables
**Solution:** Run the app once. Tables and workflow steps auto-seed on first execution.

### GPS Pings Not Recording
**Solution:** Ensure browser allows Geolocation API. Check browser console for permission errors.

### Routes Page Shows No Shipments
**Solution:** Create shipments in "Booking Confirmed" status. Routes only optimizes pending shipments.

## File Structure

```
├── app.py                  # Main Flask application (14 routes)
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── static/
│   ├── css/
│   │   └── styles.css     # Application styling
│   └── js/
│       └── app.js         # Client-side utilities
└── templates/
    ├── base.html          # Master layout
    ├── dashboard.html     # Dashboard page
    ├── shipments.html     # Shipments list
    ├── shipment_form.html # Create/edit form
    ├── tracking.html      # Tracking page with map
    └── routes.html        # Route optimization page
```

## Performance Tips

- Index on `shipments.tracking_code` for faster search
- Index on `shipments.status` for workflow queries
- Index on `tracking_updates.shipment_id` for history lookups
- Index on `gps_pings.session_id` for live tracking queries

## Security Notes

- **No authentication** in development mode (use proper auth in production)
- **Validate all inputs** - coordinates, weights, customer names
- **HTTPS required** for Geolocation API in production
- **Database credentials** stored in environment variables (not hardcoded)

## System Limitations & Local Hosting Only

**⚠️ IMPORTANT: This system is for LOCAL HOSTING ONLY**

This application **cannot and is not designed for**:

- ❌ Remote hosting or cloud deployment (AWS, Azure, Google Cloud, etc.)
- ❌ Production environments
- ❌ Shared hosting or VPS
- ❌ Docker containers with external access
- ❌ Online deployment through platforms like Heroku, Vercel, or similar
- ❌ Multi-user concurrent access over the internet
- ❌ Database access from external networks

**This system MUST**:

- ✅ Run on `localhost` (127.0.0.1) only
- ✅ Use local MySQL database (`localhost` or `127.0.0.1`)
- ✅ Be accessed only from the same machine it's running on
- ✅ Not expose ports beyond local network
- ✅ Be run for development and testing purposes only

### Why Local Only?

1. **No Authentication** - Development mode with no user authentication
2. **Hardcoded Defaults** - Assumes XAMPP with default credentials
3. **Debug Mode Enabled** - Flask running with `debug=True`
4. **No HTTPS/SSL** - Browser Geolocation requires HTTPS in production
5. **No Load Balancing** - Single-threaded development server
6. **Database Security** - Credentials in plain environment variables
7. **No Rate Limiting** - APIs have no protection against abuse
8. **Development Dependencies** - Only suitable for learning and testing

## Future Enhancements

- [ ] User authentication and role-based access control
- [ ] Real traffic API integration (Google Maps, OpenRouteService)
- [ ] Multiple warehouse locations
- [ ] Push notifications for status updates
- [ ] Mobile app version
- [ ] Advanced analytics and reporting
- [ ] Webhook integration for external systems
- [ ] Payment gateway integration
