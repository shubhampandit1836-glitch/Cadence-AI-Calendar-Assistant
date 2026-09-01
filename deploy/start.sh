#!/bin/bash
set -e

# Initialize Postgres data dir if empty (fresh container each cold start)
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    su postgres -c "/usr/lib/postgresql/*/bin/initdb -D $PGDATA"
    su postgres -c "pg_ctl -D $PGDATA -l /var/log/postgres.log start"
    sleep 3
    su postgres -c "psql --command \"CREATE USER app WITH SUPERUSER PASSWORD 'apppassword';\""
    su postgres -c "createdb -O app agentic_calendar_db"
    su postgres -c "psql -d agentic_calendar_db -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
    su postgres -c "pg_ctl -D $PGDATA stop"
fi

export DATABASE_URL="postgresql://app:apppassword@localhost:5432/agentic_calendar_db"

# Run migrations before starting services
su postgres -c "pg_ctl -D $PGDATA -l /var/log/postgres.log start"
sleep 3
cd /app/backend && DATABASE_URL=$DATABASE_URL python scripts/migrate.py
su postgres -c "pg_ctl -D $PGDATA stop"

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf