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

# Watches for files changes and restarts celery worker
# --filter watches only for pyton files
# next is entry point for celery worker
# --args arguments to pass to celery worker - it's application path to celery worker
exec watchfiles --filter python celery.__main__.main --args '-A backend.app.core.celery_app worker -l INFO'

