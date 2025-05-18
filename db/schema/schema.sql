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
    complete BOOLEAN,
    FOREIGN KEY (session) REFERENCES implants(session) ON DELETE CASCADE
);

CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL,
    date TEXT,
    task TEXT,
    results TEXT,
    FOREIGN KEY (session) REFERENCES implants(session) ON DELETE CASCADE
);


