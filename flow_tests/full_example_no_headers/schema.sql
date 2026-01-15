-- Schema for Full Example - Order Processing System
-- Drop existing tables if they exist
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS orders;

-- Orders table
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(20) UNIQUE NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    product_code VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    notification_sent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payments table
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    amount_charged DECIMAL(10, 2),
    payment_gateway VARCHAR(50),
    transaction_id VARCHAR(50),
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Index for faster lookups
CREATE INDEX idx_orders_order_id ON orders(order_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);
