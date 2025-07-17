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

# Directive 'exec' tells the shell to run the specified command
# 'uvicorn' is the webserver for python fastapi application
# host 0.0.0.0 tells the server to listen on all available network interfaces
# reload tells the application to reload if the code changes
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload