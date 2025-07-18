#!/bin/bash

# If any command exits with status non 0, script exits immediately
# Without this, scripts continue even when there is an error
set -o errexit 

# This sets non set variables as errors and exits the scripts
# Helps to catch but with undefinied variables
set -o nounset

# Ensures that script exits with non zero status if any command in the pipeline fails
# By default the status is of the status of the last command in the pipeline
set -o pipefail

# Allows to write multiline python script
python << END
import sys
import time
import psycopg

MAX_WAIT_SECONDS = 30
RETRY_INTERVAL = 5
start_time = time.time()

def check_database():
    try:
        psycopg.connect(
        dbname="${POSTGRES_DB}",
        user="${POSTGRES_USER}",
        password="${POSTGRES_PASSWORD}",
        host="${POSTGRES_HOST}",
        port="${POSTGRES_PORT}",
        )
        return True
    except psycopg.OperationalError as error:
        elapsed = int(time.time() - start_time)
        sys.stderr.write(f"Database connection attempt failed after {elapsed} seconds: {error}\n")
        return False

while True:
    if check_database():
        break
    
    if time.time() - start_time > MAX_WAIT_SECONDS:
        sys.stderr.write(f"Error: Database connection could not be established after {MAX_WAIT_SECONDS} seconds.\n")
        sys.exit(1)
    
    sys.stderr.write(f"Waiting {RETRY_INTERVAL} seconds before retrying...\n")
    time.sleep(RETRY_INTERVAL)
END

>&2 echo 'PostgreSQL is ready to accept connections'

# Passing all the arguments to the entrypoint.sh
# Replacing shell with the main process
exec "$@"
