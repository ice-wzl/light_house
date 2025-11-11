#!/bin/sh
set -e  # stop on first error

DB_PATH="database.db"
SCHEMA_PATH="schema.sql"

# Check if schema exists
if [ ! -f "$SCHEMA_PATH" ]; then
  echo "Schema file not found at: $SCHEMA_PATH"
  exit 1
fi

# Remove old DB if it exists
if [ -f "$DB_PATH" ]; then
  echo "Removing existing database: $DB_PATH"
  rm -f "$DB_PATH"
fi

# Recreate database from schema
echo "Rebuilding database from schema..."
sqlite3 "$DB_PATH" < "$SCHEMA_PATH"

echo "Database reset complete: $DB_PATH"
