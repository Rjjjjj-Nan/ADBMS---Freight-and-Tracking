# FreightFlow PH (Flask + SQLite)

A complete freight and logistics web application with:

- Dashboard for operations monitoring
- Shipment creation and management
- Predefined logistics process workflow (step-based)
- Live map tracking bounded to Philippine geographic scope
- SQLite as the advanced database backbone for operational records

## Tech Stack

- Python Flask
- SQLite (with predefined process templates)
- Leaflet + OpenStreetMap for map rendering
- HTML/CSS/JavaScript frontend

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open in your browser:

```text
http://127.0.0.1:5000
```

## Key Features

- Dashboard metrics:
  - Total shipments
  - Active shipments
  - In-transit shipments
  - Delivered shipments
- Shipment registry with search by tracking/customer/location
- Tracking updates with timeline and route polyline
- Predefined process progression:
  - Booking Confirmed
  - Picked Up
  - At Origin Hub
  - In Transit
  - At Destination Hub
  - Out for Delivery
  - Delivered
- Coordinates are validated against Philippines map bounds for realistic domestic scope

## Database

SQLite database file is auto-created on first run:

- `freight_logistics.db`

Tables:

- `process_templates`
- `shipments`
- `tracking_updates`

The app auto-seeds predefined logistics process steps on initialization.
