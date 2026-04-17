CREATE DATABASE IF NOT EXISTS logistics_db;
USE logistics_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INT,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    status ENUM('In Transit', 'Delivered', 'Delayed', 'Pending') DEFAULT 'Pending',
    cost DECIMAL(10, 2) NOT NULL,
    carrier VARCHAR(50) DEFAULT 'FedEx',
    transport_mode VARCHAR(50) DEFAULT 'Road',
    weight_kg DECIMAL(8,2) DEFAULT 100.00,
    weather_condition VARCHAR(50) DEFAULT 'Clear',
    priority VARCHAR(50) DEFAULT 'Standard',
    carbon_emissions_kg DECIMAL(10,2) DEFAULT 0.00,
    risk_score INT DEFAULT 0,
    dispatch_date DATE,
    expected_date DATE,
    delivery_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert a default admin for testing
INSERT INTO users (name, email, password, role) 
VALUES ('Admin', 'admin@gocomet.com', 'scrypt:32768:8:1$1w2x3y4z$1234567890abcdef', 'admin') 
ON DUPLICATE KEY UPDATE id=id;
