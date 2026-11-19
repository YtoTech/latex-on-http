#!/bin/bash

set -o nounset # Exit on undeclared vars
set -o errexit # Exit on command error

echo 'Running PostgreSQL migrations...'
migration_attempt=1
until goose up; do
	if [ "$migration_attempt" -ge 30 ]; then
		echo 'PostgreSQL migrations failed after 30 attempts.' >&2
		exit 1
	fi
	echo "Database unavailable; retrying migrations in 2 seconds (attempt ${migration_attempt}/30)..."
	migration_attempt=$((migration_attempt + 1))
	sleep 2
done

# Start server.
if [ "$#" -eq 1 ] && [ "$1" = 'dev' ]; then
    make debug
else
    make start
fi
