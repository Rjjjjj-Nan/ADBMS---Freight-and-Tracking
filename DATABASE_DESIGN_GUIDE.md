# Freight Logistics System - Database Design Documentation

## Table of Contents
1. [ERD Diagram](#erd-diagram)
2. [Database Normalization](#database-normalization)
3. [Data Dictionary](#data-dictionary)
4. [Database Design Strategy](#database-design-strategy)

---

## ERD Diagram

### Entity Relationship Diagram (Text-Based)

```
┌─────────────────────────────┐
│         USERS               │
├─────────────────────────────┤
│ PK: id (INT)                │
│ username (VARCHAR) - UNIQUE │
│ email (VARCHAR) - UNIQUE    │
│ password_hash (VARCHAR)     │
│ role (ENUM: admin/courier)  │
│ full_name (VARCHAR)         │
│ phone (VARCHAR)             │
│ is_active (BOOLEAN)         │
│ created_at (TIMESTAMP)      │
│ updated_at (TIMESTAMP)      │
└─────────────┬───────────────┘
              │ 1:M
              │ Manages
              │
              ▼
┌─────────────────────────────┐
│    SHIPMENT_ASSIGNMENTS     │
├─────────────────────────────┤
│ PK: id (INT)                │
│ FK: shipment_id → SHIPMENTS │
│ FK: rider_id → USERS        │
│ assigned_at (TIMESTAMP)     │
│ assignment_notes (TEXT)     │
└─────────────┬───────────────┘
              │ M:1
              │
              ▼
┌─────────────────────────────┐
│       SHIPMENTS             │
├─────────────────────────────┤
│ PK: id (INT)                │
│ reference_number (VARCHAR)  │
│ tracking_code (VARCHAR)     │
│ customer_name (VARCHAR)     │
│ origin_address (VARCHAR)    │
│ destination_address (VAR)   │
│ cargo_type (VARCHAR)        │
│ priority (ENUM)             │
│ weight_kg (DECIMAL)         │
│ status (VARCHAR)            │
│ last_lat (DOUBLE)           │
│ last_lng (DOUBLE)           │
│ expected_delivery (DATE)    │
│ current_step (INT)          │
│ created_at (TIMESTAMP)      │
│ updated_at (TIMESTAMP)      │
└─────────────┬───────────────┘
              │ 1:M
              │ Has
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│  TRACKING    │   │  GPS_TRACKING    │
│  _UPDATES    │   │  _SESSIONS       │
├──────────────┤   ├──────────────────┤
│ PK: id       │   │ PK: id           │
│ FK: shipment │   │ FK: shipment_id  │
│ _id          │   │ is_active (BOOL) │
│ status       │   │ started_at       │
│ location_    │   │ ended_at         │
│ name         │   │ created_at       │
│ latitude     │   └──────────────────┘
│ longitude    │        │ 1:M
│ notes        │        │
│ created_at   │        │ Has
└──────────────┘        ▼
                  ┌──────────────────┐
                  │    GPS_PINGS     │
                  ├──────────────────┤
                  │ PK: id           │
                  │ FK: session_id   │
                  │ latitude (DOUBLE)│
                  │ longitude (DOUBLE)
                  │ accuracy_meters  │
                  │ altitude (DOUBLE)│
                  │ created_at       │
                  └──────────────────┘

┌─────────────────────────────┐
│    PROCESS_TEMPLATES        │
├─────────────────────────────┤
│ PK: id (INT)                │
│ flow_name (VARCHAR)         │
│ step_order (INT)            │
│ step_name (VARCHAR)         │
│ description (TEXT)          │
└─────────────────────────────┘

┌─────────────────────────────┐
│    USER_SESSIONS            │
├─────────────────────────────┤
│ PK: id (INT)                │
│ FK: user_id → USERS         │
│ session_token (VARCHAR)     │
│ ip_address (VARCHAR)        │
│ user_agent (TEXT)           │
│ login_time (TIMESTAMP)      │
│ last_activity (TIMESTAMP)   │
│ expires_at (TIMESTAMP)      │
│ is_active (BOOLEAN)         │
└─────────────────────────────┘

┌─────────────────────────────┐
│     AUDIT_LOGS              │
├─────────────────────────────┤
│ PK: id (INT)                │
│ FK: user_id → USERS         │
│ action (VARCHAR)            │
│ resource_type (VARCHAR)     │
│ resource_id (INT)           │
│ old_values (JSON)           │
│ new_values (JSON)           │
│ ip_address (VARCHAR)        │
│ user_agent (TEXT)           │
│ status (VARCHAR)            │
│ details (TEXT)              │
│ created_at (TIMESTAMP)      │
└─────────────────────────────┘
```

### Relationships Summary

| Relationship | Type | Description |
|---|---|---|
| USERS → SHIPMENT_ASSIGNMENTS | 1:M | One courier can have multiple shipment assignments |
| SHIPMENTS → SHIPMENT_ASSIGNMENTS | 1:M | One shipment can be assigned to multiple couriers (scenarios) |
| SHIPMENTS → TRACKING_UPDATES | 1:M | One shipment has many location/status updates |
| SHIPMENTS → GPS_TRACKING_SESSIONS | 1:M | One shipment can have multiple GPS tracking sessions |
| GPS_TRACKING_SESSIONS → GPS_PINGS | 1:M | One session records many GPS pings/coordinates |
| USERS → USER_SESSIONS | 1:M | One user can have multiple login sessions |
| USERS → AUDIT_LOGS | 1:M | One user's actions are logged in audit trail |

---

## Database Normalization

### Normalization Process: 1NF → 2NF → 3NF

#### **Initial Unnormalized Schema (Prior to 1NF)**

```
DELIVERY_INFO
┌────────────────────────────────────────────────────────────┐
│ tracking_code | customer_info | shipment_details | riders   │
├────────────────────────────────────────────────────────────┤
│ PH2401M7K9   │ John Doe,     │ Fragile, 5kg,   │ Smith,    │
│              │ john@ex.com   │ Metro Manila    │ Rodriguez │
└────────────────────────────────────────────────────────────┘
ISSUE: Multiple values in single cells (not atomic) - violates 1NF
```

#### **First Normal Form (1NF) - Atomic Values**

**Goal**: Eliminate repeating groups and ensure all values are atomic

```
SHIPMENTS (tracking_code, customer_name, customer_email, cargo_type, weight_kg, destination)
RIDERS (rider_id, rider_name)
SHIPMENT_RIDERS (shipment_id, rider_id) - Create junction table for many-to-many
```

**What we fixed**:
- Split customer info into separate attributes
- Created junction table for multiple riders per shipment
- Each cell contains only a single value (atomic)

#### **Second Normal Form (2NF) - Remove Partial Dependencies**

**Goal**: Remove partial dependencies (non-key attributes dependent on part of composite key)

**Before 2NF (Problematic Partial Dependency)**:
```
SHIPMENT_DELIVERY
┌─────────────────────────────────────────┐
│ shipment_id | rider_id | rider_name     │
├─────────────────────────────────────────┤
│ 1           | 101      | John Smith     │  ← rider_name depends
│ 1           | 102      | Jane Rodriguez │    only on rider_id
└─────────────────────────────────────────┘
ISSUE: rider_name depends only on rider_id (part of key), not whole key
```

**After 2NF (Partial Dependencies Removed)**:
```
SHIPMENT_ASSIGNMENTS (shipment_id, rider_id, assigned_at)
USERS (id, full_name, email, phone, role)
GPS_TRACKING_SESSIONS (id, shipment_id, is_active)
```

**What we fixed**:
- Removed rider information from assignment table
- Created separate USERS table with user details
- Each non-key attribute depends on entire primary key

#### **Third Normal Form (3NF) - Remove Transitive Dependencies**

**Goal**: Eliminate transitive dependencies (X→Y, Y→Z implies X→Z problematically)

**Before 3NF (Problematic Transitive Dependency)**:
```
DELIVERIES
┌────────────────────────────────────────────┐
│ shipment_id | warehouse_name | warehouse_city │
├────────────────────────────────────────────┤
│ 1           │ Hub A          │ Manila         │  ← city depends
│ 2           │ Hub A          │ Manila         │    on warehouse_name,
│ 3           │ Hub B          │ Cebu           │    not on shipment_id
└────────────────────────────────────────────┘
ISSUE: warehouse_city depends on warehouse_name (not primary key)
```

**After 3NF (Transitive Dependencies Removed)**:
```
SHIPMENTS (id, reference_number, warehouse_id, ...)
WAREHOUSES (id, warehouse_name, warehouse_city, ...)
```

**What we fixed**:
- Separated warehouse details into dedicated table
- Removed transitive dependency chain
- Now all non-key attributes depend directly on primary key

### Final Normalized Schema (3NF Compliant)

The Freight Logistics system uses the following 3NF-compliant structure:

| Table | Why 3NF |
|---|---|
| **USERS** | PK(id) → all attributes directly; no transitive deps; role is independent |
| **SHIPMENTS** | PK(id) → all tracking info; location data atomic; no transitive deps to warehouse/process |
| **SHIPMENT_ASSIGNMENTS** | PK(id) → shipment_id + rider_id; junction table properly normalized |
| **TRACKING_UPDATES** | PK(id) → FK(shipment_id) → all location data atomic; no composite keys issues |
| **GPS_TRACKING_SESSIONS** | PK(id) → FK(shipment_id); session metadata independent |
| **GPS_PINGS** | PK(id) → FK(session_id) → coordinate data atomic; time-series data properly structured |
| **AUDIT_LOGS** | PK(id) → FK(user_id); audit data independent; JSON allows flexible value storage |

---

## Data Dictionary

### TABLE: users

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Unique identifier for each user |
| username | VARCHAR(50) | NO | UQ | - | Unique login username; 3-50 chars |
| email | VARCHAR(100) | NO | UQ | - | Unique email address; used for contact |
| password_hash | VARCHAR(255) | NO | - | - | Bcrypt-hashed password (12-round salt) |
| role | ENUM('admin', 'courier') | NO | - | courier | User role: admin (system) or courier (delivery) |
| full_name | VARCHAR(100) | YES | - | NULL | Full name of the user |
| phone | VARCHAR(20) | YES | - | NULL | Contact phone number |
| is_active | BOOLEAN | NO | - | TRUE | Account active status; soft-delete indicator |
| created_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Account creation timestamp |
| updated_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Last account modification timestamp |

**Indexes**: idx_username, idx_role, idx_active  
**Constraints**: UNIQUE(username), UNIQUE(email)

---

### TABLE: shipments

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Unique shipment identifier |
| reference_number | VARCHAR(100) | YES | - | NULL | Internal reference number |
| tracking_code | VARCHAR(20) | NO | UQ | - | Unique tracking code (format: PH+YYMMDD+5chars) |
| customer_name | VARCHAR(100) | NO | - | - | Name of shipment recipient |
| origin_address | VARCHAR(255) | NO | - | - | Pickup location address |
| destination_address | VARCHAR(255) | NO | - | - | Delivery destination address |
| cargo_type | VARCHAR(50) | NO | - | - | Type of cargo (e.g., fragile, perishable, general) |
| weight_kg | DECIMAL(10,2) | YES | - | 0.00 | Shipment weight in kilograms |
| priority | ENUM('Regular', 'Express', 'Critical') | NO | - | Regular | Delivery priority level affecting cost/time |
| status | VARCHAR(50) | NO | - | Pending | Current shipment status (Pending, In Transit, Delivered, etc.) |
| last_lat | DOUBLE | YES | - | NULL | Last recorded latitude coordinate |
| last_lng | DOUBLE | YES | - | NULL | Last recorded longitude coordinate |
| expected_delivery | DATE | YES | - | NULL | Estimated delivery date |
| current_step | INT | YES | - | 1 | Current workflow step (1-7 in standard flow) |
| created_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Shipment creation timestamp |
| updated_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Last shipment update timestamp |

**Indexes**: idx_tracking_code, idx_status, idx_created_at  
**Constraints**: UNIQUE(tracking_code), FOREIGN KEY (warehouse_id)

---

### TABLE: shipment_assignments

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Assignment record identifier |
| shipment_id | INT | NO | FK | - | References SHIPMENTS(id) |
| rider_id | INT | NO | FK | - | References USERS(id) where role='courier' |
| assigned_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | When the assignment was made |
| assignment_notes | TEXT | YES | - | NULL | Special instructions/notes for courier |

**Indexes**: idx_rider_shipments(rider_id), idx_shipment_riders(shipment_id)  
**Constraints**: UNIQUE(shipment_id, rider_id), FK(shipment_id)→SHIPMENTS, FK(rider_id)→USERS(role='courier')

---

### TABLE: tracking_updates

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Update record identifier |
| shipment_id | INT | NO | FK | - | References SHIPMENTS(id) |
| status | VARCHAR(50) | YES | - | NULL | Status at this update (e.g., "In Transit") |
| location_name | VARCHAR(255) | YES | - | NULL | Human-readable location name |
| latitude | DOUBLE | YES | - | NULL | GPS latitude coordinate |
| longitude | DOUBLE | YES | - | NULL | GPS longitude coordinate |
| notes | TEXT | YES | - | NULL | Update notes/comments |
| created_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | When this update was recorded |

**Indexes**: idx_shipment_id(shipment_id)  
**Constraints**: FK(shipment_id)→SHIPMENTS

---

### TABLE: gps_tracking_sessions

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Session identifier |
| shipment_id | INT | NO | FK | - | References SHIPMENTS(id) |
| is_active | BOOLEAN | NO | - | TRUE | Whether session is currently active |
| started_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Session start time |
| ended_at | TIMESTAMP | YES | - | NULL | Session end time (null while active) |

**Indexes**: idx_shipment_id(shipment_id), idx_is_active(is_active)  
**Constraints**: FK(shipment_id)→SHIPMENTS

---

### TABLE: gps_pings

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Ping record identifier |
| session_id | INT | NO | FK | - | References GPS_TRACKING_SESSIONS(id) |
| latitude | DOUBLE | NO | - | - | GPS latitude (validated within PH bounds: 4.5-21.5°N) |
| longitude | DOUBLE | NO | - | - | GPS longitude (validated within PH bounds: 116-127.5°E) |
| accuracy_meters | FLOAT | YES | - | NULL | GPS accuracy estimate in meters |
| altitude | FLOAT | YES | - | NULL | GPS altitude in meters |
| created_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | When ping was recorded |

**Indexes**: idx_session_id(session_id), idx_created_at(created_at)  
**Constraints**: FK(session_id)→GPS_TRACKING_SESSIONS

---

### TABLE: audit_logs

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Audit log record identifier |
| user_id | INT | YES | FK | NULL | References USERS(id); NULL for system actions |
| action | VARCHAR(100) | NO | - | - | Action performed (e.g., "create_shipment", "assign_shipment", "login") |
| resource_type | VARCHAR(50) | YES | - | NULL | Type of resource affected (shipment, user, etc.) |
| resource_id | INT | YES | - | NULL | ID of affected resource |
| old_values | JSON | YES | - | NULL | Previous values for updated fields (JSON) |
| new_values | JSON | YES | - | NULL | New values for updated fields (JSON) |
| ip_address | VARCHAR(45) | YES | - | NULL | IP address of requesting user |
| user_agent | TEXT | YES | - | NULL | HTTP user-agent of requesting browser |
| status | VARCHAR(20) | NO | - | success | Action status (success, failed, pending) |
| details | TEXT | YES | - | NULL | Additional details about the action |
| created_at | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | When action was logged |

**Indexes**: idx_user_id(user_id), idx_action(action), idx_created_at(created_at), idx_resource(resource_type, resource_id)  
**Constraints**: FK(user_id)→USERS (ON DELETE SET NULL)

---

### TABLE: user_sessions

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Session record identifier |
| user_id | INT | NO | FK | - | References USERS(id) |
| session_token | VARCHAR(255) | YES | UQ | NULL | Unique session token for validation |
| ip_address | VARCHAR(45) | YES | - | NULL | IP address of login |
| user_agent | TEXT | YES | - | NULL | Browser/client user-agent string |
| login_time | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Login timestamp |
| last_activity | TIMESTAMP | NO | - | CURRENT_TIMESTAMP | Last activity timestamp |
| expires_at | TIMESTAMP | YES | - | NULL | Session expiration time (1 hour from login) |
| is_active | BOOLEAN | NO | - | TRUE | Whether session is currently active |

**Indexes**: idx_user_id(user_id), idx_token(session_token), idx_expires(expires_at)  
**Constraints**: FK(user_id)→USERS (ON DELETE CASCADE)

---

### TABLE: process_templates

| Column | Type | Null | Key | Default | Description |
|---|---|---|---|---|---|
| id | INT | NO | PK | AUTO_INCREMENT | Template record identifier |
| flow_name | VARCHAR(100) | NO | - | - | Name of workflow (e.g., "Standard Domestic") |
| step_order | INT | NO | - | - | Sequence number in workflow (1-7) |
| step_name | VARCHAR(100) | NO | - | - | Name of this step (e.g., "Booking Confirmed", "In Transit") |
| description | TEXT | YES | - | NULL | Description of what happens at this step |

**Indexes**: idx_flow_step(flow_name, step_order)  
**Constraints**: PRIMARY KEY(flow_name, step_order)

---

## Database Design Strategy

### Fragmentation Strategy

The Freight Logistics system uses **Hybrid Fragmentation** combining vertical and horizontal approaches:

#### **Vertical Fragmentation (By Function)**

Data is divided by logical function to improve query efficiency:

```
┌─────────────────────────────────────────────────────┐
│          AUTHENTICATION FRAGMENT                    │
├─────────────────────────────────────────────────────┤
│ Tables: users, user_sessions, audit_logs           │
│ Purpose: User identity & security                  │
│ Access Pattern: Login, permission checks, audit    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│       SHIPMENT MANAGEMENT FRAGMENT                  │
├─────────────────────────────────────────────────────┤
│ Tables: shipments, shipment_assignments, process   │
│ Purpose: Core business logic                       │
│ Access Pattern: CRUD ops, filtering by status     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│         LOCATION TRACKING FRAGMENT                  │
├─────────────────────────────────────────────────────┤
│ Tables: gps_pings, tracking_updates,               │
│         gps_tracking_sessions                      │
│ Purpose: Real-time/historical location data       │
│ Access Pattern: Time-series inserts, map queries  │
└─────────────────────────────────────────────────────┘
```

**Benefits**:
- `users` queries don't load heavy GPS data
- Tracking operations isolated from auth operations
- Can replicate fragments independently (see Replication Strategy)

#### **Horizontal Fragmentation (By Date/Status)**

Time-series data can be archived:

```
Shipments table could be fragmented by status:
├─ shipments_pending (status IN ('pending', 'booking_confirmed'))
├─ shipments_in_transit (status IN ('in_transit', 'out_for_delivery'))
├─ shipments_completed (status IN ('delivered', 'cancelled'))

GPS Pings could be fragmented by age:
├─ gps_pings_current (created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY))
├─ gps_pings_archive (created_at < DATE_SUB(NOW(), INTERVAL 30 DAY))
```

**Current Status**: Not implemented in schema but infrastructure supports it

---

### Data Allocation Strategy

#### **Single-Server Deployment (Current)**

All tables stored on single MySQL instance for simplicity:

```
┌──────────────────────────────────────┐
│   Primary DB Server                  │
├──────────────────────────────────────┤
│ • All users tables                   │
│ • All shipment tables                │
│ • All tracking tables                │
│ • All audit tables                   │
│ Single source of truth               │
└──────────────────────────────────────┘
```

#### **Multi-Server Allocation (Future Scaling)**

For high-traffic scenarios:

```
┌─────────────────────┐
│   Master DB         │
├─────────────────────┤
│ ✓ users             │
│ ✓ audit_logs        │
│ ✓ shipments         │ ← All writes
│ ✓ assignments       │
│ ✓ process_templates │
└──────────┬──────────┘
           │ Replicates
  ┌────────┴────────┐
  │                 │
  ▼                 ▼
┌──────────┐  ┌──────────────────┐
│ Read1    │  │   Tracking DB    │
│ (users,  │  │  (gps_pings,     │
│ shipment │  │   tracking,      │
│  status) │  │   sessions)      │
└──────────┘  └──────────────────┘
```

**Allocation Rules**:
- **Master**: All write-heavy, transactional data
- **Read Replica 1**: User queries, authentication (low-update)
- **Tracking DB**: Location data (append-only, time-series)

---

### Replication Strategy

#### **Current: Basic Replication**

```
Master (Primary)
    ↓ Binlog replication
Slave (Backup/Read-Only)
```

**Configuration**:
```sql
-- On Master:
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%' IDENTIFIED BY 'password';

-- On Slave:
CHANGE MASTER TO
  MASTER_HOST = 'primary_db_host',
  MASTER_USER = 'repl_user',
  MASTER_PASSWORD = 'password',
  MASTER_LOG_FILE = 'mysql-bin.000001',
  MASTER_LOG_POS = 12345;
START SLAVE;
```

#### **Recommended: Multi-Tier Replication for Production**

```
┌─────────────────────────────────────────────────────────┐
│  Primary Master (Writes)                                │
├─────────────────────────────────────────────────────────┤
│ • accepts all INSERT/UPDATE/DELETE                     │
│ • generates binary logs                                │
│ • backup point every hour                              │
└───────────────┬─────────────────────────────────────────┘
                │ Replicates all data
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Slave 1  │ │ Slave 2  │ │  Analytics   │
│ (Read    │ │ (Backup) │ │  Replica     │
│ Replica) │ │          │ │  (filtered)  │
└──────────┘ └──────────┘ └──────────────┘
```

#### **Replication Strategy Details**

| Aspect | Strategy | Justification |
|---|---|---|
| **Type** | Asynchronous Binary Log Replication | Good balance of performance & consistency for logistics |
| **Log Format** | ROW-based | Captures exact data changes; better for shipment updates |
| **Slave Lag Tolerance** | <5 seconds | Acceptable for most queries; critical for real-time tracking use polling |
| **Filter Rules** | Replicate all except audit_logs (master-only) | Audit integrity; audit reads from master only |
| **Backup Strategy** | Snapshot at slave + binlog retention | Non-blocking backup; can restore to any point |
| **Failover** | Manual promotion (ops team) | Prevent split-brain in test environment; automate later |

#### **Replication Benefits**:

1. **Read Scalability**: Multiple servers handle SELECT queries
2. **High Availability**: If master fails, slave can be promoted
3. **Backup Safety**: Non-blocking backups from slave
4. **Real-time Analytics**: Can run heavy queries on analytics replica

#### **Monitoring**:

```sql
-- Check replication status on slave:
SHOW SLAVE STATUS\G

-- Monitor for issues:
-- - Seconds_Behind_Master < 5
-- - Slave_IO_Running: Yes
-- - Slave_SQL_Running: Yes
```

---

## Summary

The Freight Logistics system achieves **3NF normalization** with:
- **No data redundancy** through proper table separation
- **Data integrity** via foreign keys and constraints
- **Scalability** through fragmentation and replication strategies
- **Performance** through strategic indexing and query optimization
- **Security** through role-based access and audit logging

This design balances **consistency, performance, and maintainability** for a production freight logistics platform.
