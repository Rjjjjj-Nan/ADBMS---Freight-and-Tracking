# Freight Logistics Database Normalization Documentation

## Overview
This document provides a comprehensive analysis of the Freight Logistics Management System database design, including normalization to Boyce-Codd Normal Form (BCNF) and the security schema implementation.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Original Schema Analysis](#original-schema-analysis)
3. [Extended Schema for Security](#extended-schema-for-security)
4. [Normalization Analysis](#normalization-analysis)
5. [Entity Relationship Diagram](#entity-relationship-diagram)
6. [Table Specifications](#table-specifications)
7. [Constraints & Referential Integrity](#constraints--referential-integrity)
8. [Stored Procedures](#stored-procedures)
9. [Views](#views)
10. [Performance Optimization](#performance-optimization)
11. [Security Considerations](#security-considerations)

---

## Introduction

The Freight Logistics Management System uses a relational database design that adheres to Boyce-Codd Normal Form (BCNF) principles. The database tracks shipments, GPS tracking data, users, roles, and audit logs.

### Design Principles
- **BCNF Normalization**: Eliminates all anomalies by ensuring every determinant is a candidate key
- **Referential Integrity**: Uses foreign keys to maintain data consistency
- **Security**: Implements role-based access control (RBAC) and audit logging
- **Performance**: Includes indexes for frequently queried columns
- **Scalability**: Designed to handle growth with proper partitioning capabilities

---

## Original Schema Analysis

### Core Tables (Original)

#### 1. **gps_sessions**
Represents a GPS tracking session for a shipment.

```sql
CREATE TABLE gps_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  shipment_id INT NOT NULL,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  FOREIGN KEY (shipment_id) REFERENCES shipments(id)
);
```

**Normalization**: ✓ BCNF
- Determinant `id` → all other attributes uniquely
- No partial or transitive dependencies

#### 2. **gps_pings**
Individual GPS location pings during delivery.

```sql
CREATE TABLE gps_pings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  session_id INT NOT NULL,
  latitude DECIMAL(10,6),
  longitude DECIMAL(10,6),
  accuracy_meters DECIMAL(10,2),
  altitude DECIMAL(10,2),
  created_at TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES gps_sessions(id)
);
```

**Normalization**: ✓ BCNF
- Primary key `id` uniquely determines all other attributes
- Location data is atomic
- No dependency between non-key attributes

#### 3. **shipments**
Main shipment tracking table.

```sql
CREATE TABLE shipments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  reference_number VARCHAR(50) UNIQUE,
  origin_address TEXT,
  destination_address TEXT,
  status ENUM('pending', 'in_transit', 'delivered', 'cancelled'),
  weight_kg DECIMAL(10,2),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**Normalization**: ✓ BCNF
- Each attribute is atomic (no repeating groups)
- Status is normalized to ENUM (referential integrity)
- Address data is properly structured

### Normalization Compliance Check

| Aspect | Status | Explanation |
|--------|--------|-------------|
| 1NF (Atomic values) | ✓ Pass | All values are atomic; no repeating groups |
| 2NF (No partial dependencies) | ✓ Pass | All non-key attributes depend on full primary key |
| 3NF (No transitive dependencies) | ✓ Pass | Non-key attributes don't depend on other non-key attributes |
| BCNF (Every determinant is a key) | ✓ Pass | All determinants are candidate keys |

---

## Extended Schema for Security

### New Tables Added for Authentication & Authorization

#### 4. **users**
Stores user accounts with role-based access control.

```sql
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'rider', 'user') DEFAULT 'user',
  full_name VARCHAR(100),
  phone VARCHAR(20),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_role (role)
);
```

**Normalization Analysis**: ✓ BCNF
- **Candidate Key**: `id` (primary), `username` (unique), `email` (unique)
- **Determinants**: 
  - `id` → {username, email, password_hash, role, full_name, phone, is_active, created_at, updated_at}
  - `username` → {all attributes}
  - `email` → {all attributes}
- **Dependencies**: All non-key attributes depend solely on primary key
- **No Anomalies**:
  - Insert: Can add user anytime
  - Update: Only one record to update
  - Delete: Removing user removes only that record

#### 5. **user_sessions**
Tracks active user sessions with security information.

```sql
CREATE TABLE user_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  session_token VARCHAR(255) UNIQUE,
  ip_address VARCHAR(45),
  user_agent TEXT,
  login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_activity TIMESTAMP,
  expires_at TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Normalization Analysis**: ✓ BCNF
- **Primary Key**: `id`
- **Determinants**: All attributes depend on `id`
- **Foreign Key**: Maintains referential integrity with `users`
- **No Redundancy**: Session info stored once per session
- **Temporal Attributes**: Properly normalized as separate columns

#### 6. **shipment_assignments**
Many-to-many relationship between shipments and riders.

```sql
CREATE TABLE shipment_assignments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  shipment_id INT NOT NULL,
  rider_id INT NOT NULL,
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  assignment_notes TEXT,
  FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
  FOREIGN KEY (rider_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_assignment (shipment_id, rider_id)
);
```

**Normalization Analysis**: ✓ BCNF
- **Composite Primary Key**: (`shipment_id`, `rider_id`)
- **Candidate Keys**: `id` (surrogate), `unique_assignment` (natural)
- **Foreign Keys**: Both reference other tables
- **No Anomalies**:
  - Insert: Can assign multiple riders to one shipment
  - Update: Changes only affect specific assignment
  - Delete: Cascading delete maintains integrity

#### 7. **audit_logs**
Comprehensive audit trail of all user actions.

```sql
CREATE TABLE audit_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50),
  resource_id INT,
  old_values JSON,
  new_values JSON,
  ip_address VARCHAR(45),
  user_agent TEXT,
  status VARCHAR(20) DEFAULT 'success',
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

**Normalization Analysis**: ✓ BCNF
- **Primary Key**: `id`
- **Foreign Key**: `user_id` (optional)
- **Temporal Data**: Timestamp for compliance tracking
- **Flexibility**: JSON fields for variable-length old/new values
- **Audit Trail**: Immutable once inserted

---

## Normalization Analysis

### BCNF Compliance Table

| Table | 1NF | 2NF | 3NF | BCNF | Issues | Resolution |
|-------|-----|-----|-----|------|--------|-----------|
| gps_sessions | ✓ | ✓ | ✓ | ✓ | None | N/A |
| gps_pings | ✓ | ✓ | ✓ | ✓ | None | N/A |
| shipments | ✓ | ✓ | ✓ | ✓ | None | N/A |
| users | ✓ | ✓ | ✓ | ✓ | None | N/A |
| user_sessions | ✓ | ✓ | ✓ | ✓ | None | N/A |
| shipment_assignments | ✓ | ✓ | ✓ | ✓ | None | N/A |
| audit_logs | ✓ | ✓ | ✓ | ✓ | None | N/A |

### Key Normalization Principles Applied

1. **Atomic Values**: All values are single, indivisible
   - Example: Address stored as single TEXT field (could be normalized further if needed)

2. **No Repeating Groups**: Each cell contains one value
   - GPS coordinates: latitude and longitude as separate decimal values
   - Audit data: Flexible JSON for extensibility

3. **Functional Dependencies**:
   ```
   users: username → id, email, password_hash, role, ...
   shipment_assignments: (shipment_id, rider_id) → assigned_at, notes
   audit_logs: id → user_id, action, resource_type, ...
   ```

4. **Referential Integrity**:
   - Every foreign key references valid primary key
   - Cascading rules defined for data consistency
   - No orphaned records possible

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FREIGHT LOGISTICS DATABASE                │
└─────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │    users     │
                              ├──────────────┤
                              │ id (PK)      │
                              │ username (U) │
                              │ email (U)    │
                              │ password_hash│
                              │ role         │
                              │ full_name    │
                              │ phone        │
                              │ is_active    │
                              └──────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    │ (1:N)         │ (1:N)         │ (1:N)
                    │               │               │
            ┌───────────────┐   ┌──────────────┐   ┌─────────────────┐
            │user_sessions  │   │ audit_logs   │   │shipment_         │
            ├───────────────┤   ├──────────────┤   │assignments       │
            │ id (PK)       │   │ id (PK)      │   ├─────────────────┤
            │ user_id (FK)  │   │ user_id (FK) │   │ id (PK)         │
            │ session_token │   │ action       │   │ shipment_id (FK)│
            │ ip_address    │   │ resource_type│   │ rider_id (FK)   │
            │ expires_at    │   │ resource_id  │   │ assigned_at     │
            └───────────────┘   │ status       │   └─────────────────┘
                                │ created_at   │           │
                                └──────────────┘           │
                                                           │ (N:1)
                                                           │
                                                   ┌──────────────────┐
                                                   │   shipments      │
                                                   ├──────────────────┤
                                                   │ id (PK)          │
                                                   │ reference_number │
                                                   │ origin_address   │
                                                   │ destination_addr │
                                                   │ status           │
                                                   │ weight_kg        │
                                                   │ created_at       │
                                                   └──────────────────┘
                                                           │
                                                    (1:N)  │
                                                           │
                                                   ┌──────────────────┐
                                                   │  gps_sessions    │
                                                   ├──────────────────┤
                                                   │ id (PK)          │
                                                   │ shipment_id (FK) │
                                                   │ started_at       │
                                                   │ ended_at         │
                                                   └──────────────────┘
                                                           │
                                                    (1:N)  │
                                                           │
                                                   ┌──────────────────┐
                                                   │   gps_pings      │
                                                   ├──────────────────┤
                                                   │ id (PK)          │
                                                   │ session_id (FK)  │
                                                   │ latitude         │
                                                   │ longitude        │
                                                   │ accuracy_meters  │
                                                   │ altitude         │
                                                   │ created_at       │
                                                   └──────────────────┘

Legend:
PK = Primary Key
FK = Foreign Key
U  = Unique
(1:N) = One-to-Many relationship
(N:M) = Many-to-Many relationship
```

---

## Table Specifications

### Detailed Column Specifications

#### users table
| Column | Type | Constraints | Purpose |
|--------|------|-----------|---------|
| id | INT | PRIMARY KEY AUTO_INCREMENT | Unique user identifier |
| username | VARCHAR(50) | UNIQUE NOT NULL | Login identifier |
| email | VARCHAR(100) | UNIQUE NOT NULL | Contact email |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| role | ENUM | DEFAULT 'user' | RBAC: admin, rider, user |
| full_name | VARCHAR(100) | NULL | Display name |
| phone | VARCHAR(20) | NULL | Contact number |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation time |
| updated_at | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Last modification time |

#### shipments table
| Column | Type | Constraints | Purpose |
|--------|------|-----------|---------|
| id | INT | PRIMARY KEY AUTO_INCREMENT | Shipment identifier |
| reference_number | VARCHAR(50) | UNIQUE NOT NULL | Public reference |
| origin_address | TEXT | NOT NULL | Starting location |
| destination_address | TEXT | NOT NULL | Delivery location |
| status | ENUM | DEFAULT 'pending' | pending→in_transit→delivered/cancelled |
| weight_kg | DECIMAL(10,2) | DEFAULT 0 | Shipment weight |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Update timestamp |

#### shipment_assignments table
| Column | Type | Constraints | Purpose |
|--------|------|-----------|---------|
| id | INT | PRIMARY KEY AUTO_INCREMENT | Assignment ID |
| shipment_id | INT | FK, NOT NULL | References shipments(id) |
| rider_id | INT | FK, NOT NULL | References users(id) |
| assigned_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Assignment time |
| assignment_notes | TEXT | NULL | Special instructions |

#### audit_logs table
| Column | Type | Constraints | Purpose |
|--------|------|-----------|---------|
| id | INT | PRIMARY KEY AUTO_INCREMENT | Audit entry ID |
| user_id | INT | FK, NULL | References users(id) |
| action | VARCHAR(100) | NOT NULL | Action performed |
| resource_type | VARCHAR(50) | NULL | Type of resource affected |
| resource_id | INT | NULL | ID of affected resource |
| old_values | JSON | NULL | Previous values |
| new_values | JSON | NULL | New values |
| ip_address | VARCHAR(45) | NULL | Client IP address |
| user_agent | TEXT | NULL | Browser/client info |
| status | VARCHAR(20) | DEFAULT 'success' | Outcome status |
| details | TEXT | NULL | Additional details |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Audit timestamp |

---

## Constraints & Referential Integrity

### Foreign Key Relationships

```sql
-- user_sessions → users
ALTER TABLE user_sessions
ADD CONSTRAINT fk_user_sessions_user
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- shipment_assignments → shipments
ALTER TABLE shipment_assignments
ADD CONSTRAINT fk_assignment_shipment
FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE;

-- shipment_assignments → users
ALTER TABLE shipment_assignments
ADD CONSTRAINT fk_assignment_rider
FOREIGN KEY (rider_id) REFERENCES users(id) ON DELETE CASCADE;

-- gps_sessions → shipments
ALTER TABLE gps_sessions
ADD CONSTRAINT fk_gps_sessions_shipment
FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE;

-- gps_pings → gps_sessions
ALTER TABLE gps_pings
ADD CONSTRAINT fk_gps_pings_session
FOREIGN KEY (session_id) REFERENCES gps_sessions(id) ON DELETE CASCADE;

-- audit_logs → users
ALTER TABLE audit_logs
ADD CONSTRAINT fk_audit_logs_user
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

### Cascading Delete Rules

- **CASCADE**: When parent deleted, child records automatically deleted
  - user_sessions: If user deleted, all sessions deleted
  - shipment_assignments: If shipment/rider deleted, assignment deleted
  - gps_sessions: If shipment deleted, all GPS data deleted
  
- **SET NULL**: When parent deleted, child foreign key set to NULL
  - audit_logs: When user deleted, user_id set to NULL (preserves audit history)

### Unique Constraints

| Table | Columns | Purpose |
|-------|---------|---------|
| users | username | Only one account per username |
| users | email | Only one account per email |
| shipments | reference_number | Unique shipment identifier |
| user_sessions | session_token | Unique per session |
| shipment_assignments | (shipment_id, rider_id) | Can't assign same rider twice |

---

## Stored Procedures

### Procedure 1: GetUserShipments
**Purpose**: Role-based shipment visibility

```sql
PROCEDURE GetUserShipments(
    IN p_user_id INT,
    IN p_user_role VARCHAR(50)
)
```

**Logic**:
- **Admin**: See all shipments with rider assignments
- **Rider**: See only personally assigned shipments

**Returns**: Shipment list with relevant details

**Benefits**:
- Enforces RBAC at database level
- Single source of truth for visibility rules
- Performance optimized with GROUP_CONCAT

---

### Procedure 2: AssignShipmentToRider
**Purpose**: Transactional shipment assignment with audit logging

```sql
PROCEDURE AssignShipmentToRider(
    IN p_shipment_id INT,
    IN p_rider_id INT,
    IN p_admin_id INT,
    IN p_notes TEXT
)
```

**Logic**:
1. Verify shipment exists
2. Verify rider exists and is active
3. Insert into shipment_assignments
4. Log the action to audit_logs
5. Commit transaction

**Error Handling**: SQLEXCEPTION caught and rolled back

**Benefits**:
- Atomic operation (all-or-nothing)
- Automatic audit trail
- Validation at database level
- ACID compliance

---

### Procedure 3: GetDeliveryStatistics
**Purpose**: Dashboard statistics generation

```sql
PROCEDURE GetDeliveryStatistics(
    IN p_start_date DATE,
    IN p_end_date DATE
)
```

**Returns**:
- Total shipments
- Status breakdown (pending, in_transit, delivered, cancelled)
- Total weight handled
- Active riders count
- Average weight per rider

**Benefits**:
- Pre-computed statistics
- Single query for dashboard
- Better performance than multiple queries
- Consistent metrics

---

### Procedure 4: GetRiderPerformance
**Purpose**: Individual rider performance metrics

```sql
PROCEDURE GetRiderPerformance(
    IN p_rider_id INT,
    IN p_days_back INT
)
```

**Returns**:
- Total assignments
- Completed deliveries
- In-progress shipments
- Total weight handled
- Completion rate percentage

**Benefits**:
- Performance evaluation
- KPI tracking
- Historical analysis capability

---

## Views

### View 1: active_shipments_with_riders
**Purpose**: Join shipments with their assigned riders

```sql
SELECT 
    s.id, s.reference_number, s.origin_address,
    s.destination_address, s.status, s.weight_kg,
    u.id as rider_id, u.full_name, u.phone
FROM shipments s
LEFT JOIN shipment_assignments sa ON s.id = sa.shipment_id
LEFT JOIN users u ON sa.rider_id = u.id
WHERE s.status IN ('pending', 'in_transit');
```

**Benefits**:
- Simplified queries
- Single join point
- Consistent result set
- Useful for dashboards

### View 2: user_activity_summary
**Purpose**: User activity metrics

```sql
SELECT 
    u.id, u.username, u.role,
    COUNT(DISTINCT al.id) as total_actions,
    MAX(al.created_at) as last_action_time,
    COUNT(DISTINCT CASE WHEN DATE(al.created_at) = CURDATE() 
                       THEN al.id END) as today_actions
FROM users u
LEFT JOIN audit_logs al ON u.id = al.user_id
GROUP BY u.id;
```

**Benefits**:
- Activity monitoring
- Compliance tracking
- User engagement metrics

---

## Performance Optimization

### Indexing Strategy

```sql
-- Primary Key Indexes (implicit)
-- users.id, shipments.id, etc.

-- Unique Indexes
CREATE UNIQUE INDEX idx_username ON users(username);
CREATE UNIQUE INDEX idx_email ON users(email);
CREATE UNIQUE INDEX idx_reference_number ON shipments(reference_number);

-- Foreign Key Indexes
CREATE INDEX idx_shipment_assignments_shipment ON shipment_assignments(shipment_id);
CREATE INDEX idx_shipment_assignments_rider ON shipment_assignments(rider_id);
CREATE INDEX idx_gps_pings_session ON gps_pings(session_id);

-- Search Optimization
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_created ON shipments(created_at);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

-- Audit Log Indexes
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

### Query Optimization Tips

1. **Use indexes for**:
   - WHERE clauses (status, role, is_active)
   - JOIN conditions (foreign keys)
   - ORDER BY (created_at)
   - HAVING clauses (after grouping)

2. **Avoid**:
   - LIKE '%pattern' (leading wildcard)
   - Functions in WHERE clause
   - SELECT * (specify needed columns)
   - Correlated subqueries

3. **Best Practices**:
   - Use EXPLAIN to analyze queries
   - Monitor slow query log
   - Regularly update statistics
   - Consider partitioning for large tables

---

## Security Considerations

### 1. Authentication & Authorization

```python
# Bcrypt Hashing (12 rounds)
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

# Session Management
session["user_id"] = user["id"]
session["role"] = user["role"]
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

# Role-Based Access Control
@admin_required  # Only admin can execute
@rider_required  # Only rider/admin can execute
@login_required  # Logged-in users only
```

### 2. SQL Injection Prevention

```python
# Always use parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,)
)

# Never concatenate user input
# WRONG: f"SELECT * FROM users WHERE id = {user_id}"
# RIGHT: "SELECT * FROM users WHERE id = %s" (user_id,)
```

### 3. Audit Logging

Every action logged with:
- User ID (who)
- Action type (what)
- Timestamp (when)
- IP address (where)
- User agent (browser info)
- Before/after values (changes)

```sql
INSERT INTO audit_logs (user_id, action, ip_address, old_values, new_values)
VALUES (?, ?, ?, JSON_OBJECT(...), JSON_OBJECT(...));
```

### 4. Data Protection

- **Password Storage**: Bcrypt hashing with salt
- **Session Tokens**: Cryptographically secure random generation
- **HTTPS**: Enable in production with secure cookies
- **CORS**: Implement if using API
- **Input Validation**: Whitelist, not blacklist

### 5. Database Security

```sql
-- Minimal privileges per user
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON freight_logistics.* TO 'app_user'@'localhost';

-- No direct database access from application
-- Use connections pooling in production

-- Regular backups
-- Encryption at rest (if sensitive data)
-- Network isolation (internal only)
```

---

## Compliance & Regulations

### GDPR Compliance
- Right to access: Query user data
- Right to deletion: Handled by cascade deletes
- Data minimization: Store only necessary fields
- Audit trails: Complete history in audit_logs

### Recommendations for Production

1. **Backup Strategy**
   - Daily incremental backups
   - Weekly full backups
   - Test restore procedures
   - Off-site backup storage

2. **Monitoring**
   - Query performance monitoring
   - Slow query logs
   - Error rate tracking
   - Unusual access patterns

3. **Access Control**
   - Role-based database users
   - Connection pooling
   - VPN for remote access
   - Firewall rules

4. **Updates & Patching**
   - Regular MySQL/MariaDB updates
   - Security patches promptly
   - Test updates on staging first
   - Plan maintenance windows

---

## Appendix: Sample Queries

### A. Find all shipments assigned to a rider
```sql
SELECT s.* 
FROM shipments s
INNER JOIN shipment_assignments sa ON s.id = sa.shipment_id
WHERE sa.rider_id = 5
ORDER BY s.created_at DESC;
```

### B. Get riders with most completed shipments
```sql
SELECT u.full_name, COUNT(DISTINCT s.id) as completed
FROM users u
LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
LEFT JOIN shipments s ON sa.shipment_id = s.id AND s.status = 'delivered'
WHERE u.role = 'rider'
GROUP BY u.id
ORDER BY completed DESC
LIMIT 10;
```

### C. Audit trail for a specific shipment
```sql
SELECT al.* 
FROM audit_logs al
WHERE al.resource_type = 'shipment' 
  AND al.resource_id = 42
ORDER BY al.created_at DESC;
```

### D. User login history
```sql
SELECT al.created_at, al.ip_address, al.user_agent
FROM audit_logs al
WHERE al.user_id = 3 AND al.action = 'login'
ORDER BY al.created_at DESC
LIMIT 20;
```

---

## Conclusion

The Freight Logistics database schema is designed with:
- ✓ **BCNF Normalization**: Zero data anomalies
- ✓ **Security**: Bcrypt, SQL injection prevention, audit logging
- ✓ **Performance**: Strategic indexing and views
- ✓ **Scalability**: Proper relationships and constraints
- ✓ **Compliance**: Audit trails and data protection
- ✓ **Maintainability**: Clear structure and documentation

This design ensures data integrity, security, and performance while meeting business requirements.
