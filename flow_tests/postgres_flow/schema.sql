DROP TABLE IF EXISTS records;

CREATE TABLE records (
  policy_number TEXT PRIMARY KEY,
  amount NUMERIC(10, 2),
  status TEXT
);
