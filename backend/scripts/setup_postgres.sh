#!/bin/bash
# PostgreSQL setup script for ArtifactX
# Usage: ./setup_postgres.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - Update these for your environment
DB_NAME="${DB_NAME:-artifactx}"
DB_USER="${DB_USER:-artifactx}"
DB_PASSWORD="${DB_PASSWORD:-artifactx_password}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo -e "${YELLOW}Setting up PostgreSQL database for ArtifactX...${NC}"

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed or not in PATH${NC}"
    echo "Please install PostgreSQL client tools first."
    exit 1
fi

# Check if running as postgres user or if we can connect
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -c "SELECT 1;" > /dev/null 2>&1 || {
    echo -e "${RED}Error: Cannot connect to PostgreSQL server${NC}"
    echo "Please ensure PostgreSQL is running and you have access."
    exit 1
}

# Create database if it doesn't exist
echo "Creating database $DB_NAME..."
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || \
    echo -e "${YELLOW}Database $DB_NAME may already exist${NC}"

# Create user if it doesn't exist
echo "Creating user $DB_USER..."
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -tc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -q 1 || \
    PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
    echo -e "${YELLOW}User $DB_USER may already exist${NC}"

# Grant privileges
echo "Configuring permissions..."
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || true
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" 2>/dev/null || true
PGPASSWORD="${PGPASSWORD:-}" psql -U "${PGUSER:-postgres}" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" 2>/dev/null || true

echo -e "${GREEN}PostgreSQL setup complete!${NC}"
echo ""
echo "Update your .env file with:"
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Then run the application to create tables automatically."