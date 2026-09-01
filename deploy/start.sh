#!/bin/bash
set -e

PG_BIN=/usr/lib/postgresql/17/bin
PG_LOG=/var/lib/postgresql/data/postgres.log

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    su postgres -c "$PG_BIN/initdb -D $PGDATA"
    su postgres -c "$PG_BIN/pg_ctl -D $PGDATA -l $PG_LOG start"
    sleep 3
    su postgres -c "$PG_BIN/psql --command \"CREATE USER app WITH SUPERUSER PASSWORD 'apppassword';\""
    su postgres -c "$PG_BIN/createdb -O app agentic_calendar_db"
    su postgres -c "$PG_BIN/psql -d agentic_calendar_db -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
    su postgres -c "$PG_BIN/pg_ctl -D $PGDATA stop"
fi

export DATABASE_URL="postgresql://app:apppassword@localhost:5432/agentic_calendar_db"

su postgres -c "$PG_BIN/pg_ctl -D $PGDATA -l $PG_LOG start"
sleep 3
cd /app/backend && DATABASE_URL=$DATABASE_URL python scripts/migrate.py
su postgres -c "$PG_BIN/pg_ctl -D $PGDATA stop"

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
