-- Seed data for Full Example
-- NOTE: Data uses INCREMENTED IDs (ORD-000002 through ORD-000006)
-- because the CSV's primary key is auto-incremented before validation.
-- Original CSV has ORD-000001-000005, after increment: ORD-000002-000006

-- Insert orders (simulating batch1 import with incremented IDs)
INSERT INTO orders (order_id, customer_name, product_code, quantity, unit_price, total_amount, order_date, status, notification_sent)
VALUES
    ('ORD-000002', 'John Smith', 'PROD-001', 5, 29.99, 149.95, '2024-01-15', 'COMPLETED', 1),
    ('ORD-000003', 'Jane Doe', 'PROD-002', 3, 49.99, 149.97, '2024-01-16', 'COMPLETED', 1),
    ('ORD-000004', 'Bob Wilson', 'PROD-003', 10, 9.99, 99.90, '2024-01-17', 'COMPLETED', 1),
    ('ORD-000005', 'Alice Brown', 'PROD-001', 2, 29.99, 59.98, '2024-01-18', 'COMPLETED', 1),
    ('ORD-000006', 'Charlie Davis', 'PROD-004', 1, 199.99, 199.99, '2024-01-19', 'COMPLETED', 1);

-- Insert payments (simulating batch2 payment processing)
INSERT INTO payments (order_id, payment_status, amount_charged, payment_gateway, transaction_id, processed_at)
VALUES
    ('ORD-000002', 'SUCCESS', 149.95, 'mock', 'TXN-001', CURRENT_TIMESTAMP),
    ('ORD-000003', 'SUCCESS', 149.97, 'mock', 'TXN-002', CURRENT_TIMESTAMP),
    ('ORD-000004', 'SUCCESS', 99.90, 'mock', 'TXN-003', CURRENT_TIMESTAMP),
    ('ORD-000005', 'SUCCESS', 59.98, 'mock', 'TXN-004', CURRENT_TIMESTAMP),
    ('ORD-000006', 'SUCCESS', 199.99, 'mock', 'TXN-005', CURRENT_TIMESTAMP);
