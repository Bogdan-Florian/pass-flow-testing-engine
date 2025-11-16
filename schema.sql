-- SQL schema for the Insurance Validation Suite

-- Drop tables if they exist to ensure a clean slate
DROP TABLE IF EXISTS operations;
DROP TABLE IF EXISTS policy_premiums;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS parties;

-- Create the 'parties' table to store customer information
CREATE TABLE parties (
    party_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    -- THE FIX: The 'UNIQUE' keyword is removed to allow the seed script
    -- to create a duplicate SSN for testing purposes.
    ssn TEXT NOT NULL 
);

-- Create the main 'policies' table
CREATE TABLE policies (
    policy_number TEXT PRIMARY KEY,
    party_id TEXT NOT NULL,
    product_code TEXT NOT NULL,
    status TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_premium NUMERIC NOT NULL,
    num_premiums INTEGER NOT NULL,
    FOREIGN KEY (party_id) REFERENCES parties(party_id)
);

-- Create 'policy_premiums' to track monthly payments/installments
CREATE TABLE policy_premiums (
    premium_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_number TEXT NOT NULL,
    premium_amount NUMERIC NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (policy_number) REFERENCES policies(policy_number)
);

-- Create 'operations' as an audit log for key policy events
CREATE TABLE operations (
    operation_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_number TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    operation_date DATE NOT NULL,
    description TEXT,
    FOREIGN KEY (policy_number) REFERENCES policies(policy_number)
);
