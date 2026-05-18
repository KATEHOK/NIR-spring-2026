#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || { echo "Failed to cd to $PROJECT_ROOT"; exit 1; }
mkdir -p .secrets

openssl rand -base64 32 | tr -d '\n' > .secrets/db_password
openssl rand -base64 32 | tr -d '\n' > .secrets/redis_password
openssl rand -hex 64 > .secrets/secret_key

chmod 600 .secrets/db_password
chmod 600 .secrets/redis_password
chmod 600 .secrets/secret_key