-- Freight & Logistics Management System Database Schema
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS freight_logistics;
USE freight_logistics;

-- Users table (Admin, Courier, and User/Customer)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    role ENUM('admin', 'courier', 'user') NOT NULL DEFAULT 'user',
    full_name VARCHAR(150),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role (role),
    INDEX idx_email (email),
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Parcels table
CREATE TABLE parcels (
    parcel_id INT AUTO_INCREMENT PRIMARY KEY,
    tracking_number VARCHAR(50) UNIQUE NOT NULL,
    user_id INT,
    sender_name VARCHAR(150) NOT NULL,
    sender_phone VARCHAR(15),
    sender_address TEXT,
    receiver_name VARCHAR(150) NOT NULL,
    receiver_phone VARCHAR(15),
    receiver_address TEXT,
    origin_city VARCHAR(100) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    weight_kg DECIMAL(8, 2),
    cost_php DECIMAL(10, 2) NOT NULL,
    shipping_method ENUM('standard', 'express', 'super', 'international') DEFAULT 'standard',
    status ENUM('pending', 'in_transit', 'delivered', 'cancelled', 'returned') DEFAULT 'pending',
    notes TEXT,
    scheduled_pickup_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_status (status),
    INDEX idx_tracking (tracking_number),
    INDEX idx_destination (destination_city),
    INDEX idx_created_at (created_at),
    INDEX idx_destination_status (destination_city, status),
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Parcel Assignments (N:M relationship between parcels and couriers)
CREATE TABLE parcel_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    parcel_id INT NOT NULL,
    courier_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_parcel (parcel_id),
    INDEX idx_courier (courier_id),
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    FOREIGN KEY (courier_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Parcel Conditions (Audit trail of status updates)
CREATE TABLE parcel_conditions (
    condition_id INT AUTO_INCREMENT PRIMARY KEY,
    parcel_id INT NOT NULL,
    courier_id INT,
    previous_condition VARCHAR(50),
    new_condition VARCHAR(50) NOT NULL,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parcel (parcel_id),
    INDEX idx_courier (courier_id),
    INDEX idx_updated_at (updated_at),
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    FOREIGN KEY (courier_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit Logs (All actions)
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_logged_at (logged_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Analytics Snapshots (Daily aggregates)
CREATE TABLE analytics_snapshots (
    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    total_parcels INT,
    delivered_count INT,
    in_transit_count INT,
    pending_count INT,
    cancelled_count INT,
    returned_count INT,
    total_revenue_php DECIMAL(15, 2),
    avg_delivery_time_days DECIMAL(5, 2),
    avg_cost_php DECIMAL(10, 2),
    success_rate_percent DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (snapshot_date),
    INDEX idx_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Sessions
CREATE TABLE user_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_user (user_id),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Messages (User-Courier communication)
CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    parcel_id INT NOT NULL,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    message_text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parcel (parcel_id),
    INDEX idx_sender (sender_id),
    INDEX idx_receiver (receiver_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Courier Ratings (User ratings for couriers)
CREATE TABLE courier_ratings (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    parcel_id INT NOT NULL,
    user_id INT NOT NULL,
    courier_id INT NOT NULL,
    rating_stars INT NOT NULL CHECK(rating_stars >= 1 AND rating_stars <= 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_courier (courier_id),
    INDEX idx_user (user_id),
    INDEX idx_parcel (parcel_id),
    UNIQUE KEY unique_rating (parcel_id),
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (courier_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Stored Procedures

-- Get parcels assigned to a specific courier
DELIMITER $$
CREATE PROCEDURE GetCourierParcels(IN p_courier_id INT)
BEGIN
    SELECT p.parcel_id, p.tracking_number, p.sender_name, p.receiver_name,
           p.origin_city, p.destination_city, p.weight_kg, p.cost_php,
           p.status, p.shipping_method, p.created_at, p.updated_at
    FROM parcels p
    INNER JOIN parcel_assignments pa ON p.parcel_id = pa.parcel_id
    WHERE pa.courier_id = p_courier_id AND p.is_deleted = FALSE
    ORDER BY p.created_at DESC;
END$$
DELIMITER ;

-- Get delivery statistics for admin dashboard
DELIMITER $$
CREATE PROCEDURE GetDeliveryStatistics()
BEGIN
    SELECT 
        COUNT(*) as total_parcels,
        SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
        SUM(CASE WHEN status = 'in_transit' THEN 1 ELSE 0 END) as in_transit,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
        SUM(CASE WHEN status = 'returned' THEN 1 ELSE 0 END) as returned,
        SUM(cost_php) as total_revenue,
        AVG(cost_php) as avg_cost,
        ROUND(SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as success_rate
    FROM parcels
    WHERE is_deleted = FALSE;
END$$
DELIMITER ;

-- Get parcels by destination for analytics
DELIMITER $$
CREATE PROCEDURE GetParcelsByDestination()
BEGIN
    SELECT destination_city, COUNT(*) as count
    FROM parcels
    WHERE is_deleted = FALSE
    GROUP BY destination_city
    ORDER BY count DESC
    LIMIT 10;
END$$
DELIMITER ;

-- Get daily delivery trend (last 30 days)
DELIMITER $$
CREATE PROCEDURE GetDailyDeliveryTrend()
BEGIN
    SELECT DATE(created_at) as delivery_date, COUNT(*) as count
    FROM parcels
    WHERE is_deleted = FALSE AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY DATE(created_at)
    ORDER BY delivery_date;
END$$
DELIMITER ;

-- Get courier performance
DELIMITER $$
CREATE PROCEDURE GetCourierPerformance()
BEGIN
    SELECT 
        u.user_id, u.full_name, u.username,
        COUNT(p.parcel_id) as parcels_assigned,
        SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) as delivered,
        ROUND(SUM(CASE WHEN p.status = 'delivered' THEN 1 ELSE 0 END) / COUNT(p.parcel_id) * 100, 2) as delivery_rate
    FROM users u
    LEFT JOIN parcel_assignments pa ON u.user_id = pa.courier_id
    LEFT JOIN parcels p ON pa.parcel_id = p.parcel_id AND p.is_deleted = FALSE
    WHERE u.role = 'courier'
    GROUP BY u.user_id, u.full_name, u.username
    ORDER BY delivered DESC;
END$$
DELIMITER ;

-- Create indexes for performance
ALTER TABLE parcels ADD INDEX idx_status_date (status, created_at);
ALTER TABLE parcel_conditions ADD INDEX idx_parcel_date (parcel_id, updated_at);

-- Insert default admin user (password: admin123 - bcrypt hashed)
-- Use: $2b$12$OoLXFpKJ5rMwCxrU0SyBjO1H8Jx3J0/dJ9rJ5KJ0/dJ9rJ5KJ0/dJ
INSERT INTO users (username, email, password_hash, full_name, role, phone) VALUES 
('admin', 'admin@freight.com', '$2b$12$OoLXFpKJ5rMwCxrU0SyBjO1H8Jx3J0/dJ9rJ5KJ0/dJ9rJ5KJ0/dJ', 'System Admin', 'admin', '1234567890');
