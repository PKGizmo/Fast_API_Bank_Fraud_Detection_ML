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

# Command to setup and run the flower service
# First line - entry point to celery worker
# 2nd line - module containing the celery app
# 3rd line - broker url
# 4th line - flower starts the flower service
# 5th line - address 0.0.0.0 ensures that flower binds to all network interfaces
# 6th line - port 5555 is a port that flower listens on
# 7th line - basic authentication for the flower service
FLOWER_CMD="celery \
    -A backend.app.core.celery_app \
    -b ${CELERY_BROKER_URL} \
    flower \
    --address=0.0.0.0 \
    --port=5555 \
    --basic_auth=${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}"

# We're using watchfiles to monitor changes in python files and restart the flower
# service 
exec watchfiles \
    --filter python \
    --ignore-paths '.venv,venv,_myutils,.git,__pycache__,*.pyc' \
    "${FLOWER_CMD}"