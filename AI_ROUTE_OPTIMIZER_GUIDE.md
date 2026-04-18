# AI Route Optimizer & Auto-Cancellation Guide

## Overview

Your freight logistics system now includes intelligent route optimization and automated decision-making features:

### 🚚 **AI Route Optimizer**
- Calculates optimal delivery routes using nearest-neighbor algorithm
- Estimates delivery times based on distance and road conditions
- Calculates delivery costs with priority multipliers
- Visualizes routes on interactive Leaflet map
- Shows detailed delivery sequence

### ⚠️ **Auto-Cancellation Logic**
- Automatically cancels shipments in "Booking Confirmed" status after 3+ days
- No manual intervention needed
- Prevents operational waste and customer dissatisfaction
- Logged in tracking history for audit trail

---

## Features in Detail

### 1. Route Optimization Algorithm

**How It Works:**
- Uses **Nearest Neighbor Algorithm** starting from Manila warehouse (14.5995°N, 120.9842°E)
- For each shipment, selects the closest unvisited destination
- Builds efficient delivery sequence to minimize travel distance

**Distance Calculation:**
- Uses **Haversine Formula** for accurate great-circle distance
- Calculates distance between Philippine coordinates in kilometers

**Delivery Time Estimation:**
- Based on 40 km/h average road speed
- Plus 1 hour processing per hub
- Range: 1-48 hours
- Formula: `(distance_km / 40) + 1`

**Cost Estimation:**
- Base cost: ₱100
- Per kilometer: ₱5
- Priority multipliers:
  - Regular: 1.0x (₱100 + ₱5/km)
  - Express: 1.5x (₱150 + ₱7.50/km)
  - Critical: 2.0x (₱200 + ₱10/km)

**Optimization Criteria:**
1. **Distance** - Routes are ordered by proximity
2. **Time** - Faster routes prioritized for critical shipments
3. **Cost** - Priority levels affect delivery pricing

### 2. Auto-Cancellation Rules

**Trigger Condition:**
- Shipments in "Booking Confirmed" status for 3+ days
- Checked automatically on dashboard load and routes page load

**What Happens:**
1. Status changes to "Cancelled"
2. Automatic note added: "Auto-cancelled: Not processed within 3 days"
3. Logged in tracking_updates table with timestamp
4. No warehouse resources wasted on stalled bookings

**Benefits:**
- Reduces operational waste
- Prevents customer service issues from delays
- Frees up warehouse space
- Fully automated - no admin review needed
- Audit trail maintained in database

### 3. At-Risk Shipment Warnings

**Visual Indicators:**
- Dashboard shows "At Risk ⚠️" metric card when shipments are pending 2+ days
- Routes page displays red alert box highlighting shipments about to be cancelled
- Table shows days pending for each at-risk shipment

**Example:**
- Day 0-1: Normal processing
- Day 2: Warning on dashboard
- Day 3+: Automatically cancelled

---

## How to Use

### Accessing the AI Route Optimizer

**Option 1: Dashboard Button**
1. Go to Dashboard (`http://localhost:5000/dashboard`)
2. Click "AI Route Optimizer" button (blue button)
3. View optimized routes

**Option 2: Navigation Menu**
1. Click "Routes" in the top navigation bar
2. Automatically loads optimized delivery routes

### Viewing Optimized Routes

The Routes page displays:

1. **At-Risk Shipments Alert** (if any)
   - Shows shipments pending 3+ days
   - Indicates which ones will be auto-cancelled
   - Provides tracking links for each

2. **Route Metrics Summary**
   - Total route distance (km)
   - Estimated delivery time (hours)
   - Total estimated cost (₱)
   - Number of shipments

3. **Interactive Map**
   - Red marker: Manila warehouse (hub)
   - Blue markers: Delivery destinations
   - Dashed line: Optimized route path
   - Click markers for details

4. **Delivery Sequence Table**
   - Shows optimized order (#1, #2, #3, etc.)
   - Tracking code and destination
   - Priority level (color-coded)
   - Distance from previous stop (km)
   - Estimated delivery time (hours)
   - Estimated cost (₱)
   - Cargo type and weight

### Understanding the Visualization

**Map Colors:**
- 🔴 Red: Warehouse hub
- 🔵 Blue: Delivery stops in optimal sequence
- 🔵🔵🔵: Connected by dashed line showing route

**Table Colors:**
- 🟠 Orange row: Critical priority
- 🔵 Blue row: Express priority
- ⚪ White row: Regular priority

---

## API Endpoints

### `/routes` (GET)
- View optimized routes for pending shipments
- Auto-cancels overdue shipments
- Returns HTML page with map and table

**Response:**
- optimized_route: List of shipments in optimal order
- route_metrics: Total distance, time, cost
- at_risk_shipments: Pending 2+ days
- Interactive Leaflet map visualization

### `/api/routes/optimize` (POST)
- REST API for route optimization
- Filter by priority or get all pending

**Request JSON:**
```json
{
  "priority": "all",  // or "Regular", "Express", "Critical"
  "max_shipments": 50
}
```

**Response JSON:**
```json
{
  "route": [
    {
      "id": 123,
      "tracking_code": "PH260410123AB",
      "destination": "Quezon City",
      "priority": "Express",
      "dest_lat": 14.6349,
      "dest_lng": 121.0388,
      "distance_from_prev": 25.5,
      "delivery_time_hrs": 1.64,
      "estimated_cost": 225.75,
      "route_sequence": 1
    }
  ],
  "metrics": {
    "distance": 500.25,
    "time_hours": 24.5,
    "cost": 5250.00,
    "shipment_count": 10
  }
}
```

---

## Database Changes

### New Fields in `shipments` Table
- `status`: Now includes "Cancelled" as a valid status
- `created_at`: Used to calculate if shipment is overdue

### New Records in `tracking_updates` Table
- Auto-cancellation adds entry with:
  - status: "Cancelled"
  - location_name: "System"
  - notes: "Auto-cancelled: Not processed within 3 days"
  - created_at: Timestamp of cancellation

---

## Examples

### Example 1: View Optimized Route
1. Go to `http://localhost:5000/routes`
2. See 10 pending shipments sorted by nearest-neighbor
3. Map shows Manila warehouse and all 10 delivery points
4. Table shows optimal sequence with distances and costs

### Example 2: Auto-Cancellation Trigger
1. Shipment created on Day 0: Status = "Booking Confirmed"
2. Day 3: Dashboard automatically cancels it
3. Dashboard "At Risk" card no longer shows it
4. Tracking history shows cancellation note
5. No manual intervention needed

### Example 3: Cost Comparison
- Regular 50km shipment: ₱100 + (₱5 × 50) = **₱350**
- Express 50km shipment: ₱150 + (₱7.50 × 50) = **₱525**
- Critical 50km shipment: ₱200 + (₱10 × 50) = **₱700**

---

## Technical Architecture

### Functions in `app_mysql.py`

**Distance Calculation:**
```python
def haversine_distance(lat1, lon1, lat2, lon2)
```
- Calculates great-circle distance
- Returns distance in kilometers

**Time Estimation:**
```python
def estimate_delivery_time(distance_km)
```
- Assumes 40 km/h road speed
- Adds 1 hour processing
- Clamps between 1-48 hours

**Cost Calculation:**
```python
def estimate_delivery_cost(distance_km, priority)
```
- Base + per-km rate with priority multiplier
- Returns cost in PHP

**Route Optimization:**
```python
def optimize_route_nearest_neighbor(shipments, warehouse_lat, warehouse_lng)
```
- Implements nearest-neighbor algorithm
- Returns list of shipments in optimal order

**Route Metrics:**
```python
def calculate_route_metrics(route, warehouse_lat, warehouse_lng)
```
- Calculates total distance
- Estimates total time and cost
- Returns metrics dictionary

**Auto-Cancellation:**
```python
def auto_cancel_overdue_shipments(cursor, db)
```
- Finds shipments pending 3+ days
- Updates status to "Cancelled"
- Logs in tracking_updates
- Called on dashboard and routes page load

---

## Monitoring & Maintenance

### Daily Operations
1. Dashboard automatically runs auto-cancellation check
2. Check "At Risk ⚠️" metric for pending shipments
3. Use Routes page to optimize delivery schedules
4. Monitor at-risk shipments in red alert box

### Weekly Review
1. Check cancelled shipments in database
2. Review optimization decisions
3. Adjust warehouse location if needed
4. Monitor average delivery times vs estimates

### Database Monitoring
```sql
-- View all cancelled shipments
SELECT tracking_code, customer_name, destination, status, created_at 
FROM shipments 
WHERE status = 'Cancelled';

-- View at-risk shipments
SELECT tracking_code, customer_name, destination, created_at 
FROM shipments 
WHERE status = 'Booking Confirmed' 
  AND created_at <= DATE_SUB(NOW(), INTERVAL 2 DAY);

-- View optimization history
SELECT shipment_id, status, location_name, notes, created_at 
FROM tracking_updates 
WHERE notes LIKE '%Auto-cancelled%';
```

---

## Customization

### Changing 3-Day Cancellation Threshold
Edit `app_mysql.py`, function `auto_cancel_overdue_shipments()`:
```python
three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()  # Change "3" to desired days
```

### Changing Warehouse Location
Edit `/routes` route in `app_mysql.py`:
```python
warehouse_lat, warehouse_lng = 14.5995, 120.9842  # Change to new coordinates
```

### Adjusting Cost Formula
Edit `estimate_delivery_cost()`:
```python
base_cost = 100  # Change base cost
per_km_cost = 5  # Change per-km rate
```

### Changing Delivery Speed Assumption
Edit `estimate_delivery_time()`:
```python
hours = (distance_km / 40) + 1  # Change "40" to different km/h
```

---

## Troubleshooting

### No Routes Showing
- Ensure shipments exist with status: "Booking Confirmed", "Picked Up", or "At Origin Hub"
- Check MySQL connection is working
- Verify shipment coordinates are within Philippines bounds (4.5-21.5°N, 116-127.5°E)

### Map Not Loading
- Ensure Leaflet CDN is accessible (https://unpkg.com/leaflet@1.9.4)
- Check browser console for errors
- Verify shipment coordinates are valid numbers

### Auto-Cancellation Not Working
- Check that MySQL server is running
- Verify process_templates table has 7 rows
- Check created_at timestamp format is ISO 8601
- Review app.py logs for SQL errors

---

## Performance Considerations

### Scalability
- Nearest-neighbor algorithm is O(n²) - suitable for < 1000 shipments per route
- For larger operations, consider optimized TSP algorithms
- Database queries use indexes on status and created_at

### Optimization Tips
1. Limit route to 50-100 shipments per optimize call
2. Use filters by priority to group similar deliveries
3. Run optimization during off-peak hours
4. Consider splitting large routes into regional sub-routes

---

## Future Enhancements

Potential improvements:
- [ ] Multiple warehouse/hub locations
- [ ] Traffic/road conditions API integration
- [ ] Customer time window preferences
- [ ] Vehicle capacity constraints
- [ ] Real-time route adjustments
- [ ] Machine learning for demand forecasting
- [ ] SMS/Email notifications for at-risk shipments
- [ ] Advanced TSP algorithms (Ant Colony, Genetic Algorithm)
- [ ] Multi-day route planning
- [ ] Driver assignment and load balancing
