PRAGMA foreign_keys = ON;

CREATE TABLE implants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT UNIQUE NOT NULL,
    first_checkin TEXT,
    last_checkin TEXT,
    alive BOOLEAN,
    callback_freq INTEGER, -- Minutes
    jitter INTEGER,         -- Integer treated as % of callback_freq
    username TEXT,
    hostname TEXT
);

CREATE TABLE tasking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL,
    date TEXT,
    task TEXT,
    args TEXT,
    complete Text, -- True/False/Pending
    FOREIGN KEY (session) REFERENCES implants(session) ON DELETE CASCADE
);

CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tasking_id INTEGER NOT NULL,
    session TEXT NOT NULL,
    date TEXT,
    task TEXT,
    args TEXT,
    results TEXT,
    FOREIGN KEY (session) REFERENCES implants(session) ON DELETE CASCADE,
    FOREIGN KEY (tasking_id) REFERENCES tasking(id) ON DELETE CASCADE
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- - Add default user to users table
INSERT INTO users (username, password, created_at) VALUES ('admin', 'password', datetime('now'));
