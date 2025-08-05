#!/bin/bash

set -o nounset # Exit on undeclared vars
set -o errexit # Exit on command error

echo 'Running PostgreSQL migrations...'
# Wait for database to fire-up.
if [ "$#" -eq 1 ] && [ "$1" = 'dev' ]; then
	sleep 3
fi
ls /app/latex-on-http/tools
# goose up

# Start server.
if [ "$#" -eq 1 ] && [ "$1" = 'dev' ]; then
    make debug
else
    make start
fi
