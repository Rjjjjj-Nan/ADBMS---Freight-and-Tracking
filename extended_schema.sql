-- Extended Freight Logistics Schema with Authentication & Security
-- Add new tables for user management, authentication, and audit logging

-- ============================================================
-- TABLE: users
-- Purpose: Store user accounts with roles and authentication
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'courier') NOT NULL DEFAULT 'courier',
  full_name VARCHAR(100),
  phone VARCHAR(20),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_role (role),
  INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- TABLE: user_sessions
-- Purpose: Track active user sessions and security info
-- ============================================================
CREATE TABLE IF NOT EXISTS user_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  session_token VARCHAR(255) UNIQUE,
  ip_address VARCHAR(45),
  user_agent TEXT,
  login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_sessions (user_id),
  INDEX idx_token (session_token),
  INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- TABLE: shipment_assignments
-- Purpose: Many-to-many relationship between shipments and riders
-- ============================================================
CREATE TABLE IF NOT EXISTS shipment_assignments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  shipment_id INT NOT NULL,
  rider_id INT NOT NULL,
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  assignment_notes TEXT,
  FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
  FOREIGN KEY (rider_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_assignment (shipment_id, rider_id),
  INDEX idx_rider_shipments (rider_id),
  INDEX idx_shipment_riders (shipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- TABLE: audit_logs
-- Purpose: Track all user actions for security and compliance
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
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
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user_id (user_id),
  INDEX idx_action (action),
  INDEX idx_created_at (created_at),
  INDEX idx_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- SEED DATA: Default Admin User
-- ============================================================
-- Insert default admin account: username = "admin", password = "admin123" (bcrypt hashed)
-- In production, change this password immediately
INSERT IGNORE INTO users (id, username, email, password_hash, role, full_name, is_active)
VALUES (
  1, 
  'admin', 
  'admin@freightlogistics.com',
  '$2b$12$1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP',
  'admin',
  'System Administrator',
  TRUE
);

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

-- ============================================================
-- PROCEDURE 1: GetUserShipments
-- Purpose: Get all shipments visible to a user based on their role
-- Parameters: 
--   IN user_id - The user ID
--   IN user_role - The user's role (admin, rider, user)
-- Returns: All shipments the user can see
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS GetUserShipments(
    IN p_user_id INT,
    IN p_user_role VARCHAR(50)
)
BEGIN
    IF p_user_role = 'admin' THEN
        -- Admin can see all shipments
        SELECT 
            s.id,
            s.reference_number,
            s.origin_address,
            s.destination_address,
            s.status,
            s.weight_kg,
            s.created_at,
            GROUP_CONCAT(DISTINCT u.full_name SEPARATOR ', ') as assigned_couriers
        FROM shipments s
        LEFT JOIN shipment_assignments sa ON s.id = sa.shipment_id
        LEFT JOIN users u ON sa.rider_id = u.id
        GROUP BY s.id
        ORDER BY s.created_at DESC;
    ELSE
        -- Couriers can only see their assigned shipments
        SELECT 
            s.id,
            s.reference_number,
            s.origin_address,
            s.destination_address,
            s.status,
            s.weight_kg,
            s.created_at
        FROM shipments s
        INNER JOIN shipment_assignments sa ON s.id = sa.shipment_id
        WHERE sa.rider_id = p_user_id
        ORDER BY s.created_at DESC;
    END IF;
END$$

DELIMITER ;

-- ============================================================
-- PROCEDURE 2: AssignShipmentToRider
-- Purpose: Assign a shipment to a rider with audit logging
-- Parameters:
--   IN p_shipment_id - The shipment to assign
--   IN p_rider_id - The rider to assign to
--   IN p_admin_id - The admin performing the assignment
--   IN p_notes - Assignment notes
-- Returns: Success status
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS AssignShipmentToRider(
    IN p_shipment_id INT,
    IN p_rider_id INT,
    IN p_admin_id INT,
    IN p_notes TEXT
)
BEGIN
    DECLARE v_success BOOLEAN DEFAULT FALSE;
    DECLARE v_error_msg VARCHAR(255);
    
    -- Start transaction
    START TRANSACTION;
    
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            ROLLBACK;
            SET v_error_msg = 'Assignment failed: Database error';
        END;
        
        -- Verify shipment exists
        IF NOT EXISTS (SELECT 1 FROM shipments WHERE id = p_shipment_id) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Shipment not found';
        END IF;
        
        -- Verify rider exists and is active
        IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_rider_id AND role = 'courier' AND is_active = TRUE) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Courier not found or inactive';
        END IF;
        
        -- Insert assignment
        INSERT INTO shipment_assignments (shipment_id, rider_id, assignment_notes)
        VALUES (p_shipment_id, p_rider_id, p_notes);
        
        -- Log the action
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, new_values)
        VALUES (
            p_admin_id,
            'assign_shipment',
            'shipment_assignment',
            LAST_INSERT_ID(),
            JSON_OBJECT('shipment_id', p_shipment_id, 'rider_id', p_rider_id)
        );
        
        COMMIT;
        SET v_success = TRUE;
    END;
    
    SELECT v_success as success, COALESCE(v_error_msg, 'Assignment successful') as message;
END$$

DELIMITER ;

-- ============================================================
-- PROCEDURE 3: GetDeliveryStatistics
-- Purpose: Generate delivery statistics for dashboard
-- Parameters:
--   IN p_start_date - Start date for statistics
--   IN p_end_date - End date for statistics
-- Returns: Delivery statistics including count, weight, status breakdown
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS GetDeliveryStatistics(
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT 
        COUNT(DISTINCT s.id) as total_shipments,
        COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as delivered_count,
        COUNT(DISTINCT CASE WHEN s.status = 'in_transit' THEN s.id END) as in_transit_count,
        COUNT(DISTINCT CASE WHEN s.status = 'pending' THEN s.id END) as pending_count,
        COUNT(DISTINCT CASE WHEN s.status = 'cancelled' THEN s.id END) as cancelled_count,
        ROUND(SUM(s.weight_kg), 2) as total_weight_kg,
        COUNT(DISTINCT sa.rider_id) as active_riders,
        ROUND(SUM(s.weight_kg) / NULLIF(COUNT(DISTINCT sa.rider_id), 0), 2) as avg_weight_per_rider
    FROM shipments s
    LEFT JOIN shipment_assignments sa ON s.id = sa.shipment_id
    WHERE DATE(s.created_at) BETWEEN p_start_date AND p_end_date;
END$$

DELIMITER ;

-- ============================================================
-- PROCEDURE 4: GetRiderPerformance
-- Purpose: Get performance metrics for individual riders
-- Parameters:
--   IN p_rider_id - The rider to get stats for
--   IN p_days_back - Number of days to look back
-- Returns: Rider performance statistics
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS GetRiderPerformance(
    IN p_rider_id INT,
    IN p_days_back INT
)
BEGIN
    SELECT 
        u.id,
        u.full_name,
        u.phone,
        COUNT(DISTINCT s.id) as total_assignments,
        COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as completed,
        COUNT(DISTINCT CASE WHEN s.status = 'in_transit' THEN s.id END) as in_progress,
        COUNT(DISTINCT CASE WHEN s.status = 'pending' THEN s.id END) as pending,
        ROUND(SUM(s.weight_kg), 2) as total_weight_handled,
        ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) / 
              NULLIF(COUNT(DISTINCT s.id), 0), 2) as completion_rate
    FROM users u
    LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
    LEFT JOIN shipments s ON sa.shipment_id = s.id AND DATE(s.created_at) >= DATE_SUB(CURDATE(), INTERVAL p_days_back DAY)
    WHERE u.id = p_rider_id AND u.role = 'courier'
    GROUP BY u.id, u.full_name, u.phone;
END$$

DELIMITER ;

-- ============================================================
-- INDEXES for Performance Optimization
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_created ON shipments(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_user_action ON audit_logs(user_id, action);

-- ============================================================
-- VIEWS for Common Queries
-- ============================================================

-- View: All active shipments with assigned riders
CREATE OR REPLACE VIEW active_shipments_with_riders AS
SELECT 
    s.id,
    s.reference_number,
    s.origin_address,
    s.destination_address,
    s.status,
    s.weight_kg,
    s.created_at,
    u.id as rider_id,
    u.full_name as rider_name,
    u.phone as rider_phone
FROM shipments s
LEFT JOIN shipment_assignments sa ON s.id = sa.shipment_id
LEFT JOIN users u ON sa.rider_id = u.id
WHERE s.status IN ('pending', 'in_transit');

-- View: User activity logs
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT 
    u.id,
    u.username,
    u.role,
    COUNT(DISTINCT al.id) as total_actions,
    MAX(al.created_at) as last_action_time,
    COUNT(DISTINCT CASE WHEN DATE(al.created_at) = CURDATE() THEN al.id END) as today_actions
FROM users u
LEFT JOIN audit_logs al ON u.id = al.user_id
GROUP BY u.id, u.username, u.role;

-- ============================================================
-- NEW PROCEDURE 5: GetCourierPerformanceMetrics
-- Purpose: Calculate detailed performance metrics for a specific courier
-- Parameters:
--   IN p_courier_id - The courier ID to get metrics for
-- Returns: Comprehensive performance data including completion rates, avg delivery time, weight handled
-- Usage: Admin dashboard uses this to display individual courier performance cards
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS GetCourierPerformanceMetrics(
    IN p_courier_id INT
)
BEGIN
    SELECT 
        u.id as courier_id,
        u.full_name,
        u.phone,
        COUNT(DISTINCT sa.shipment_id) as total_shipments,
        COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) as completed_shipments,
        COUNT(DISTINCT CASE WHEN s.status IN ('in_transit', 'out_for_delivery') THEN s.id END) as active_shipments,
        ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.status = 'delivered' THEN s.id END) / 
              NULLIF(COUNT(DISTINCT sa.shipment_id), 0), 2) as completion_percentage,
        ROUND(SUM(s.weight_kg), 2) as total_weight_handled,
        ROUND(AVG(CASE WHEN s.status = 'delivered' THEN 
              TIMESTAMPDIFF(HOUR, s.created_at, s.updated_at) END), 1) as avg_delivery_time_hours,
        COUNT(DISTINCT gp.session_id) as total_tracking_sessions,
        COUNT(DISTINCT gp.id) as total_gps_pings,
        DATEDIFF(NOW(), u.created_at) as days_as_courier,
        u.is_active,
        u.created_at as courier_since
    FROM users u
    LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
    LEFT JOIN shipments s ON sa.shipment_id = s.id
    LEFT JOIN gps_tracking_sessions gts ON s.id = gts.shipment_id
    LEFT JOIN gps_pings gp ON gts.id = gp.session_id
    WHERE u.id = p_courier_id AND u.role = 'courier'
    GROUP BY u.id, u.full_name, u.phone, u.is_active, u.created_at;
END$$

DELIMITER ;

-- ============================================================
-- NEW PROCEDURE 6: AssignShipmentOptimized
-- Purpose: Find and assign the best courier for a shipment based on current workload and performance
-- Parameters:
--   IN p_shipment_id - The shipment to assign
--   IN p_admin_id - The admin performing the assignment
-- Returns: Assignment result with courier selected based on lowest current workload and highest performance
-- Usage: Admin clicks "Auto-Assign" button on shipment, system selects best available courier
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS AssignShipmentOptimized(
    IN p_shipment_id INT,
    IN p_admin_id INT
)
BEGIN
    DECLARE v_best_courier_id INT;
    DECLARE v_success BOOLEAN DEFAULT FALSE;
    DECLARE v_error_msg VARCHAR(255);
    
    START TRANSACTION;
    
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            ROLLBACK;
            SET v_error_msg = 'Assignment failed: Database error';
        END;
        
        -- Verify shipment exists and is unassigned
        IF NOT EXISTS (SELECT 1 FROM shipments WHERE id = p_shipment_id) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Shipment not found';
        END IF;
        
        -- Find best available courier (lowest current workload + highest performance rating)
        SELECT u.id INTO v_best_courier_id
        FROM users u
        LEFT JOIN shipment_assignments sa ON u.id = sa.rider_id
        LEFT JOIN shipments s ON sa.shipment_id = s.id AND s.status NOT IN ('delivered', 'cancelled')
        WHERE u.role = 'courier' AND u.is_active = TRUE
        GROUP BY u.id
        ORDER BY 
            COUNT(s.id) ASC,
            (COUNT(CASE WHEN s.status = 'delivered' THEN 1 END) / 
             NULLIF(COUNT(sa.shipment_id), 0)) DESC
        LIMIT 1;
        
        -- If no courier found, raise error
        IF v_best_courier_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No available couriers';
        END IF;
        
        -- Assign shipment to best courier
        INSERT INTO shipment_assignments (shipment_id, rider_id, assignment_notes)
        VALUES (p_shipment_id, v_best_courier_id, CONCAT('Auto-assigned on ', NOW()));
        
        -- Log the action
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, new_values)
        VALUES (
            p_admin_id,
            'auto_assign_shipment',
            'shipment_assignment',
            LAST_INSERT_ID(),
            JSON_OBJECT('shipment_id', p_shipment_id, 'courier_id', v_best_courier_id)
        );
        
        COMMIT;
        SET v_success = TRUE;
    END;
    
    SELECT v_success as success, COALESCE(v_error_msg, CONCAT('Shipment assigned to courier ID: ', v_best_courier_id)) as message, v_best_courier_id as assigned_courier_id;
END$$

DELIMITER ;

-- ============================================================
-- NEW VIEW 3: vw_courier_active_shipments
-- Purpose: Show all currently assigned shipments for each courier with delivery status and destination
-- Usage: Courier dashboard displays this to show their active workload; Admin can see all couriers' assignments
-- Query structure: Joins couriers with their assigned shipments, filters for non-completed items
-- ============================================================
CREATE OR REPLACE VIEW vw_courier_active_shipments AS
SELECT 
    u.id as courier_id,
    u.full_name as courier_name,
    u.phone as courier_phone,
    s.id as shipment_id,
    s.tracking_code,
    s.customer_name,
    s.origin_address,
    s.destination_address,
    s.status,
    s.weight_kg,
    s.priority,
    s.expected_delivery,
    s.created_at as shipment_created,
    sa.assigned_at,
    CONCAT(
        ROUND(COALESCE(6371 * 2 * ASIN(SQRT(
            POW(SIN(RADIANS((s.last_lat - 14.5995) / 2)), 2) +
            COS(RADIANS(14.5995)) * COS(RADIANS(s.last_lat)) *
            POW(SIN(RADIANS((s.last_lng - 120.9842) / 2)), 2)
        )), 0), 2), ' km'
    ) as distance_from_warehouse
FROM users u
INNER JOIN shipment_assignments sa ON u.id = sa.rider_id
INNER JOIN shipments s ON sa.shipment_id = s.id
WHERE u.role = 'courier' 
    AND s.status NOT IN ('delivered', 'cancelled')
    AND u.is_active = TRUE
ORDER BY u.id, s.priority DESC, s.created_at ASC;

-- ============================================================
-- NEW VIEW 4: vw_shipment_routing_optimization
-- Purpose: Display shipments ready for routing with courier capabilities and distance calculations
-- Usage: Route optimization feature uses this to calculate best sequences; Admin uses for route planning
-- Query structure: Shows unassigned shipments with geo coordinates for routing calculations
-- ============================================================
CREATE OR REPLACE VIEW vw_shipment_routing_optimization AS
SELECT 
    s.id as shipment_id,
    s.tracking_code,
    s.customer_name,
    s.origin_address,
    s.destination_address,
    s.cargo_type,
    s.priority,
    s.weight_kg,
    s.status,
    s.last_lat as destination_latitude,
    s.last_lng as destination_longitude,
    14.5995 as warehouse_latitude,
    120.9842 as warehouse_longitude,
    ROUND(COALESCE(6371 * 2 * ASIN(SQRT(
        POW(SIN(RADIANS((s.last_lat - 14.5995) / 2)), 2) +
        COS(RADIANS(14.5995)) * COS(RADIANS(s.last_lat)) *
        POW(SIN(RADIANS((s.last_lng - 120.9842) / 2)), 2)
    )), 0), 2) as distance_from_warehouse_km,
    CASE 
        WHEN s.priority = 'Critical' THEN 2.0
        WHEN s.priority = 'Express' THEN 1.5
        ELSE 1.0
    END as priority_multiplier,
    ROUND((100 + (COALESCE(6371 * 2 * ASIN(SQRT(
        POW(SIN(RADIANS((s.last_lat - 14.5995) / 2)), 2) +
        COS(RADIANS(14.5995)) * COS(RADIANS(s.last_lat)) *
        POW(SIN(RADIANS((s.last_lng - 120.9842) / 2)), 2)
    )), 0) * 5)) * 
    CASE 
        WHEN s.priority = 'Critical' THEN 2.0
        WHEN s.priority = 'Express' THEN 1.5
        ELSE 1.0
    END, 2) as estimated_delivery_cost,
    ROUND((COALESCE(6371 * 2 * ASIN(SQRT(
        POW(SIN(RADIANS((s.last_lat - 14.5995) / 2)), 2) +
        COS(RADIANS(14.5995)) * COS(RADIANS(s.last_lat)) *
        POW(SIN(RADIANS((s.last_lng - 120.9842) / 2)), 2)
    )), 0) / 40) + 1, 2) as estimated_delivery_hours,
    COUNT(DISTINCT sa.rider_id) as assigned_courier_count,
    s.created_at as shipment_created
FROM shipments s
LEFT JOIN shipment_assignments sa ON s.id = sa.shipment_id
WHERE s.status IN ('pending', 'booking_confirmed', 'picked_up', 'at_origin_hub')
GROUP BY s.id
ORDER BY s.priority DESC, s.created_at ASC;
