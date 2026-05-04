# Courier Management Enhancement - Summary of Changes

## Overview
This update adds comprehensive courier management features to the Freight & Logistics system, including:
- Courier ratings display on the admin dashboard
- Complete courier management interface
- Courier activation/deactivation functionality
- Detailed performance reports
- Customer ratings & reviews management

---

## Features Added

### 1. **Courier Ratings Display** ⭐
- **Location**: Admin Dashboard
- **Changes**:
  - Updated `GetCourierPerformance` stored procedure to include:
    - Average rating score (1-5 stars)
    - Total number of ratings
    - Total revenue from deliveries
    - Email and phone information
    - Active status
  - Modified admin dashboard template to display ratings in a table format
  - Added "Manage Couriers" button to dashboard

### 2. **Courier Management Page** 👥
- **Route**: `/admin/couriers`
- **Features**:
  - View all couriers with statistics (active/inactive)
  - Quick stats cards showing:
    - Total couriers count
    - Active couriers count
    - Inactive couriers count
  - Search functionality (search by name, email, phone)
  - Deactivate/Reactivate buttons with confirmation modals
  - Status badges (Active/Inactive)
  - View, Edit, and Action buttons for each courier

### 3. **Courier Details Page** 📊
- **Route**: `/admin/couriers/<courier_id>/view`
- **Features**:
  - Comprehensive courier profile card
  - Performance metrics:
    - Total parcels assigned
    - Successfully delivered
    - In transit count
    - Pending count
    - Cancelled count
    - Delivery rate percentage
  - Customer satisfaction metrics:
    - Average rating (out of 5 stars)
    - Customer review count
    - Average delivery time in days
    - Total revenue generated
  - Recent parcels table (last 20)
  - Customer reviews section (last 10)
  - Edit and Deactivate/Activate buttons

### 4. **Courier Edit Page** ✏️
- **Route**: `/admin/couriers/<courier_id>/edit`
- **Features**:
  - Edit courier information:
    - Full name
    - Email address
    - Phone number
  - Pre-filled form with current data
  - Status display (read-only)
  - Save and cancel buttons

### 5. **Courier Deactivation/Activation** 🔐
- **Routes**:
  - `/admin/couriers/<courier_id>/deactivate` (POST)
  - `/admin/couriers/<courier_id>/activate` (POST)
- **Features**:
  - Confirmation modals before action
  - Prevents deactivated couriers from accepting new parcels
  - Preserves all account data
  - Audit logging of all actions
  - Real-time UI updates after action

### 6. **Courier Performance Report** 📈
- **Route**: `/admin/reports/courier-performance`
- **Features**:
  - Performance leaderboard sorted by rating and delivery rate
  - Quick statistics:
    - Total couriers
    - Average delivery rate across all couriers
    - Average customer rating
    - Total revenue
  - Detailed performance table with:
    - Rank/position
    - Courier name and status
    - Parcels assigned and delivered
    - Delivery rate (with progress bar)
    - Customer rating and review count
    - Average delivery time
    - Revenue generated
  - Top performers sections:
    - Top 3 Rated couriers
    - Highest Delivery Rate couriers
    - Top Revenue couriers

### 7. **Courier Ratings & Reviews Report** 🎯
- **Route**: `/admin/reports/courier-ratings`
- **Features**:
  - Filter options:
    - By specific courier
    - By minimum rating (1-5 stars)
  - Sort options:
    - Newest first (default)
    - Oldest first
    - Highest rating
    - Lowest rating
  - Detailed review display showing:
    - Courier name and courier ID
    - Star rating (visual stars)
    - Customer comment
    - Customer name
    - Date and time of review
    - Related parcel tracking number
    - Sender and receiver names
  - Summary statistics:
    - Total ratings count
    - Average rating
    - 5-star review count
    - 1-2 star review count

---

## Database Changes

### Updated Stored Procedure: `GetCourierPerformance`
**New fields added:**
```sql
- u.email (courier email)
- u.phone (courier phone)
- u.is_active (active status)
- COALESCE(ROUND(AVG(cr.rating_stars), 2), 0) as avg_rating
- COUNT(DISTINCT cr.rating_id) as total_ratings
- COALESCE(SUM(CASE WHEN p.status = 'delivered' THEN p.cost_php ELSE 0 END), 0) as total_revenue
```

The procedure now joins with `courier_ratings` table to calculate average ratings.

---

## New Backend Routes

1. **`/admin/couriers`** - List and manage all couriers
2. **`/admin/couriers/<id>/deactivate`** - Deactivate courier (POST)
3. **`/admin/couriers/<id>/activate`** - Reactivate courier (POST)
4. **`/admin/couriers/<id>/view`** - View courier details
5. **`/admin/couriers/<id>/edit`** - Edit courier information
6. **`/admin/reports/courier-performance`** - Performance report
7. **`/admin/reports/courier-ratings`** - Ratings & reviews report

---

## New Templates

1. **`admin_couriers.html`** - Courier management list with search and actions
2. **`admin_courier_detail.html`** - Detailed courier profile and statistics
3. **`admin_courier_edit.html`** - Courier information edit form
4. **`admin_performance_report.html`** - Performance leaderboard and analytics
5. **`admin_ratings_report.html`** - Ratings and reviews with filtering

---

## Modified Templates

1. **`admin_dashboard.html`** - Enhanced with:
   - Quick action buttons (Manage Couriers, Performance, Ratings)
   - New courier performance table with ratings
   - Removed chart that was replaced with detailed table

---

## Frontend Features

### Search & Filter
- Real-time search across courier name, email, and phone
- Filter ratings by star level
- Filter by specific courier
- Sort reviews by newest, oldest, highest, or lowest

### User Interface
- Responsive design for all screen sizes
- Bootstrap modals for confirmations
- Progress bars for delivery rates
- Star ratings display (visual stars)
- Status badges (Active/Inactive, color-coded)
- Color-coded performance indicators

### Interactivity
- AJAX requests for deactivate/activate without page reload
- Confirmation modals before destructive actions
- Real-time table updates
- Tooltips for buttons
- Sortable leaderboard

---

## Audit Logging

All management actions are logged:
- Courier deactivation
- Courier activation
- Courier information updates
- User IP address and user agent recorded

---

## How to Use

### As an Admin:

1. **Access Courier Management**:
   - Go to Admin Dashboard → Click "Manage Couriers" button

2. **View Courier Details**:
   - Click the eye icon (View) on any courier row
   - See comprehensive statistics, recent parcels, and customer reviews

3. **Edit Courier Information**:
   - From courier detail page, click "Edit Information"
   - Update name, email, or phone
   - Click "Save Changes"

4. **Deactivate a Courier**:
   - Click the lock icon (Deactivate) on courier list or detail page
   - Confirm in the modal
   - Courier will no longer be able to accept new parcels

5. **Reactivate a Courier**:
   - Click the unlock icon (Reactivate) on inactive courier
   - Confirm in the modal
   - Courier can now accept new parcels again

6. **View Performance Report**:
   - Go to Admin Dashboard → Click "Performance" button
   - See all couriers ranked by rating and delivery performance
   - View top performers in different categories

7. **View Ratings Report**:
   - Go to Admin Dashboard → Click "Ratings" button
   - Filter by courier or minimum star rating
   - Sort by newest, oldest, highest, or lowest
   - Read detailed customer reviews

---

## Benefits

✅ **Better Monitoring**: Track courier performance with detailed metrics  
✅ **Quality Control**: Monitor ratings and customer feedback in real-time  
✅ **Easy Management**: Activate/deactivate couriers without deletion  
✅ **Data Preservation**: All courier data is preserved when deactivated  
✅ **Insights**: Generate detailed reports for performance analysis  
✅ **Accountability**: Complete audit trail of all management actions  
✅ **Search & Filter**: Quickly find couriers and specific reviews  

---

## Next Steps (Optional Enhancements)

- Add courier performance alerts (low ratings)
- Implement automated courier warnings/notifications
- Add bulk actions for multiple couriers
- Generate downloadable performance reports (PDF/CSV)
- Implement performance-based incentive tracking
- Add delivery time SLAs per courier
- Create supervisor/manager roles with limited access

