DROP TABLE IF EXISTS policies;

CREATE TABLE policies (
  policy_number TEXT PRIMARY KEY,
  amount NUMERIC(10, 2),
  status TEXT
);
