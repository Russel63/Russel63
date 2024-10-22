CREATE TABLE transactions (
    transactions_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    sign TEXT NOT NULL,
    value INTEGER NOT NULL,
    price FLOAT NOT NULL,
    time TEXT NOT NULL
);

CREATE TABLE owners (
    sign TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    value INTEGER NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    exp NUMERIC NOT NULL DEFAULT 0,
    aspects TEXT
);
